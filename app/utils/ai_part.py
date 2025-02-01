from transformers import BertTokenizer
import torch
from keybert import KeyBERT
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from transformers import pipeline

ALLOWED_EXTENSIONS = {'pdf'}

# Helper function to check file extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

keybertmodel = KeyBERT('distilbert-base-nli-mean-tokens')

tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
# model = BertModel.from_pretrained('bert-base-uncased')

# Initialize lemmatizer
lemmatizer = WordNetLemmatizer()

def get_bert_embedding(text):
    """
    Generate BERT embedding for the given text.
    """
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
    outputs = keybertmodel(**inputs)
    # Use the mean of the last hidden state as the embedding
    embedding = outputs.last_hidden_state.mean(dim=1).detach().numpy()
    return embedding

def lemmatize_text(text):
    words = word_tokenize(text)
    lemmatized_words = [lemmatizer.lemmatize(word) for word in words]
    return " ".join(lemmatized_words)

# Load a pre-trained text classification pipeline for toxicity detection
def load_toxicity_model():
    """
    Initializes and returns a pre-trained NLP pipeline for toxicity detection
    with hardware acceleration.
    """
    # Detect device (mps for Apple Silicon, cuda for NVIDIA, cpu fallback)
    device = 0 if torch.cuda.is_available() else -1  # cuda if available
    if not torch.cuda.is_available() and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = "mps"  # Use MPS if available

    return pipeline("text-classification", model="unitary/toxic-bert", tokenizer="unitary/toxic-bert", device=device)

def is_abusive(content, threshold=0.5, max_token_length=512):
    # Load the toxicity detection model
    toxicity_detector = load_toxicity_model()

    # Split content into chunks of max_token_length
    content_chunks = [content[i:i+max_token_length] for i in range(0, len(content), max_token_length)]

    abusive = False
    all_predictions = []

    for chunk in content_chunks:
        predictions = toxicity_detector(chunk)
        all_predictions.extend(predictions)

        # Check if the chunk is abusive
        if any(pred["label"].lower() == "toxic" and pred["score"] >= threshold for pred in predictions):
            abusive = True
            break  # Stop processing further if any chunk is abusive

    return abusive, all_predictions


