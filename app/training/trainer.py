"""
Trainer - Clase principal para entrenamiento de modelos LLM.
"""

import logging
import time
from pathlib import Path
from typing import List, Optional, Callable
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    Trainer,
    TrainingArguments,
    DataCollatorForLanguageModeling,
    TrainerCallback
)
from datasets import Dataset

logger = logging.getLogger(__name__)


class ProgressCallback(TrainerCallback):
    """Callback para reportar progreso durante el entrenamiento."""
    
    def __init__(self, progress_callback: Optional[Callable] = None):
        self.progress_callback = progress_callback
    
    def on_log(self, args, state, control, logs=None, **kwargs):
        """Se llama cuando el trainer hace logging."""
        if self.progress_callback and logs:
            self.progress_callback(
                epoch=int(state.epoch) if state.epoch else 0,
                loss=logs.get('loss', 0.0),
                step=state.global_step,
                total_steps=state.max_steps
            )


class LLMTrainer:
    """
    Entrenador de modelos LLM con fine-tuning.
    Refactorizado del llm_trainer.py original para uso en API y CLI.
    """
    
    def __init__(
        self,
        model_name: str,
        training_data: List[str],
        output_dir: Path,
        config: dict = None
    ):
        """
        Inicializa el entrenador.
        
        Args:
            model_name: Nombre del modelo base (ej: gpt2, flax-community/gpt-2-spanish)
            training_data: Lista de textos para entrenamiento
            output_dir: Directorio donde guardar el modelo entrenado
            config: Configuración del entrenamiento (epochs, batch_size, etc.)
        """
        self.model_name = model_name
        self.training_data = training_data
        self.output_dir = output_dir
        self.config = config or {}
        
        # Configuración por defecto
        self.num_train_epochs = self.config.get("epochs", 3)
        self.per_device_train_batch_size = self.config.get("batch_size", 4)
        self.learning_rate = self.config.get("learning_rate", 5e-5)
        self.max_length = self.config.get("max_length", 128)
        
        # Progreso callback
        self.progress_callback: Optional[Callable] = None
        
        # Modelo y tokenizer
        self.tokenizer = None
        self.model = None
    
    def set_progress_callback(self, callback: Callable):
        """
        Establece una función callback para reportar progreso.
        
        Args:
            callback: Función con firma (epoch, loss, step, total_steps)
        """
        self.progress_callback = callback
    
    def load_model_and_tokenizer(self):
        """Carga el modelo y tokenizer."""
        logger.info(f"Loading model: {self.model_name}")
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                clean_up_tokenization_spaces=True
            )
            self.model = AutoModelForCausalLM.from_pretrained(self.model_name)
            
            # Asignar pad token si no existe
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            logger.info("Model and tokenizer loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading model {self.model_name}: {e}")
            raise
    
    def prepare_dataset(self) -> Dataset:
        """
        Prepara el dataset tokenizado.
        
        Returns:
            Dataset tokenizado listo para entrenamiento
        """
        if not self.training_data:
            raise ValueError("No training data provided")
        
        logger.info(f"Preparing dataset with {len(self.training_data)} lines...")
        
        def tokenize_function(example):
            """Tokeniza y agrega labels."""
            tokenized = self.tokenizer(
                example["text"],
                padding="max_length",
                truncation=True,
                max_length=self.max_length
            )
            # Los labels son una copia de input_ids para language modeling
            tokenized["labels"] = tokenized["input_ids"].copy()
            return tokenized
        
        try:
            # Crear dataset raw
            raw_dataset = Dataset.from_dict({"text": self.training_data})
            
            # Tokenizar
            tokenized_dataset = raw_dataset.map(
                tokenize_function,
                batched=True,
                remove_columns=["text"]
            )
            
            logger.info(f"Dataset prepared: {len(tokenized_dataset)} samples")
            return tokenized_dataset
            
        except Exception as e:
            logger.error(f"Error preparing dataset: {e}")
            raise
    
    def create_training_arguments(self) -> TrainingArguments:
        """Crea argumentos de entrenamiento."""
        # Crear timestamp para output
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        output_path = self.output_dir / f"{self.model_name.replace('/', '_')}_{timestamp}"
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Training output will be saved to: {output_path}")
        
        return TrainingArguments(
            output_dir=str(output_path),
            overwrite_output_dir=True,
            num_train_epochs=self.num_train_epochs,
            per_device_train_batch_size=self.per_device_train_batch_size,
            learning_rate=self.learning_rate,
            save_steps=500,
            save_total_limit=2,
            logging_dir=str(output_path / "logs"),
            logging_steps=10,
            evaluation_strategy="no",
            report_to=[],  # No reportar a wandb u otros
            logging_first_step=True,
        )
    
    def train(self) -> str:
        """
        Ejecuta el entrenamiento completo.
        
        Returns:
            Ruta del modelo guardado
        """
        if not self.training_data:
            raise ValueError("No training data provided")
        
        logger.info(f"Starting training with {len(self.training_data)} samples...")
        logger.info(f"Config: epochs={self.num_train_epochs}, batch_size={self.per_device_train_batch_size}, lr={self.learning_rate}")
        
        try:
            # Cargar modelo
            self.load_model_and_tokenizer()
            
            # Preparar dataset
            tokenized_dataset = self.prepare_dataset()
            
            # Argumentos de entrenamiento
            training_args = self.create_training_arguments()
            
            # Data collator para language modeling
            data_collator = DataCollatorForLanguageModeling(
                tokenizer=self.tokenizer,
                mlm=False  # No masked language modeling, solo causal LM
            )
            
            # Crear trainer
            logger.info("Initializing Trainer...")
            
            # Callback para progreso
            callbacks = []
            if self.progress_callback:
                callbacks.append(ProgressCallback(self.progress_callback))
            
            trainer = Trainer(
                model=self.model,
                args=training_args,
                train_dataset=tokenized_dataset,
                data_collator=data_collator,
                callbacks=callbacks,
            )
            
            # Entrenar
            logger.info("Training started...")
            trainer.train()
            
            # Guardar modelo y tokenizer
            output_path = Path(training_args.output_dir)
            trainer.save_model(output_path)
            self.tokenizer.save_pretrained(output_path)
            
            logger.info(f"✓ Training completed successfully!")
            logger.info(f"✓ Model saved at: {output_path}")
            
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Training error: {e}")
            raise
    
    @staticmethod
    def get_available_models() -> dict:
        """
        Retorna lista de modelos base disponibles.
        
        Returns:
            Diccionario con modelos por categoría
        """
        return {
            "english": [
                {
                    "name": "gpt2",
                    "description": "GPT-2 base (124M params) - Rápido, inglés",
                    "size": "124M"
                },
                {
                    "name": "gpt2-medium",
                    "description": "GPT-2 medium (355M params) - Mejor calidad",
                    "size": "355M"
                },
                {
                    "name": "distilgpt2",
                    "description": "DistilGPT-2 (82M params) - Muy rápido",
                    "size": "82M"
                },
                {
                    "name": "EleutherAI/gpt-neo-125M",
                    "description": "GPT-Neo 125M - Alternativa a GPT-2",
                    "size": "125M"
                }
            ],
            "spanish": [
                {
                    "name": "datificate/gpt2-small-spanish",
                    "description": "GPT-2 Small Spanish - Español optimizado",
                    "size": "124M"
                },
                {
                    "name": "flax-community/gpt-2-spanish",
                    "description": "GPT-2 Spanish - Comunidad Flax",
                    "size": "124M"
                }
            ],
            "multilingual": [
                {
                    "name": "bigscience/bloom-560m",
                    "description": "BLOOM 560M - Multilingüe, 46 idiomas",
                    "size": "560M"
                }
            ]
        }
