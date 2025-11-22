from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from typing import Optional, Union, List, Dict

class HuggingFaceProvider:
    def __init__(self, model_name: str, model=None, tokenizer=None):
        """
        Inicializa el proveedor de HuggingFace.
        
        Args:
            model_name: Nombre o path del modelo
            model: Modelo ya cargado (opcional)
            tokenizer: Tokenizer ya cargado (opcional)
        """
        if model is not None and tokenizer is not None:
            # Usar modelo y tokenizer ya cargados
            self.model = model
            self.tokenizer = tokenizer
        else:
            # Cargar modelo y tokenizer desde nombre
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(model_name)
        
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

    async def generate(
        self, 
        prompt: Union[str, List[Dict[str, str]]], 
        max_length: int = 50, 
        num_return_sequences: int = 1, 
        temperature: float = 0.7
    ):
        """
        Genera texto usando el modelo HuggingFace.
        
        Args:
            prompt: Puede ser string simple o lista de mensajes (formato OpenAI)
            max_length: Se usa como max_new_tokens (número de tokens a generar)
            num_return_sequences: Número de secuencias a generar
            temperature: Temperatura para la generación
        """
        # Convertir formato de mensajes a string si es necesario
        if isinstance(prompt, list):
            # Formato de mensajes (estilo OpenAI)
            text = ""
            for msg in prompt:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    text += f"System: {content}\n\n"
                elif role == "user":
                    text += f"User: {content}\n"
                elif role == "assistant":
                    text += f"Assistant: {content}\n"
            text += "Assistant: "
            prompt = text
        
        # Truncar el prompt si es muy largo
        enc = self.tokenizer(prompt, return_tensors="pt", padding=True, truncation=True, max_length=512)
        with torch.no_grad():
            out = self.model.generate(
                enc["input_ids"],
                attention_mask=enc["attention_mask"],
                max_new_tokens=max_length,  # Usar max_new_tokens en lugar de max_length
                num_return_sequences=num_return_sequences,
                do_sample=True,
                temperature=temperature,
                pad_token_id=self.tokenizer.pad_token_id
            )
        return self.tokenizer.decode(out[0], skip_special_tokens=True)
