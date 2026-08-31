from transformers import AutoTokenizer, AutoModel

MODEL = "same_model_name_here"

tokenizer = AutoTokenizer.from_pretrained(MODEL)
model = AutoModel.from_pretrained(MODEL)
