from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

class HuggingFaceProvider:
    def __init__(self, model_name: str):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name)
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

    def generate(self, prompt: str, max_length: int = 50, temperature: float = 0.7):
        enc = self.tokenizer(prompt, return_tensors="pt", padding=True, truncation=True, max_length=max_length)
        with torch.no_grad():
            out = self.model.generate(
                enc["input_ids"],
                attention_mask=enc["attention_mask"],
                max_length=max_length,
                do_sample=True,
                temperature=temperature,
                pad_token_id=self.tokenizer.pad_token_id
            )
        return self.tokenizer.decode(out[0], skip_special_tokens=True)
