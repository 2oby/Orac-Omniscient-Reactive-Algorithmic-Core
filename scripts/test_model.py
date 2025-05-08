from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

def main():
    # Load model and tokenizer
    model_name = "gpt2"  # We'll start with a small model for testing
    print(f"Loading model: {model_name}")
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)
    
    # Test prompt
    prompt = "Once upon a time"
    print(f"\nSending test prompt: '{prompt}'")
    
    # Tokenize and generate
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(
        inputs["input_ids"],
        max_length=50,
        num_return_sequences=1,
        no_repeat_ngram_size=2
    )
    
    # Decode and print the result
    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    print("\nGenerated text:")
    print(generated_text)

if __name__ == "__main__":
    main() 