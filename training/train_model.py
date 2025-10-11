import os
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
import pickle
import glob
from tqdm import tqdm
import time

# Configuration
SEQUENCE_LENGTH = 120  # ~4 seconds at 30fps (longer for better action detection)
BATCH_SIZE = 32
EPOCHS = 100
LEARNING_RATE = 0.001
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

class LandmarkDataset(Dataset):
    def __init__(self, sequences, labels):
        self.sequences = torch.FloatTensor(sequences)
        self.labels = torch.LongTensor(labels)
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        return self.sequences[idx], self.labels[idx]

class TinyLSTM(nn.Module):
    """Tiny LSTM model optimized for Raspberry Pi CPU inference."""
    def __init__(self, input_size, hidden_size1=16, hidden_size2=8, num_classes=3):
        super(TinyLSTM, self).__init__()
        
        self.lstm1 = nn.LSTM(input_size, hidden_size1, batch_first=True)
        self.dropout1 = nn.Dropout(0.2)
        
        self.lstm2 = nn.LSTM(hidden_size1, hidden_size2, batch_first=True)
        self.dropout2 = nn.Dropout(0.2)
        
        self.fc1 = nn.Linear(hidden_size2, 32)
        self.dropout3 = nn.Dropout(0.2)
        self.fc2 = nn.Linear(32, num_classes)
        
        self.relu = nn.ReLU()
    
    def forward(self, x):
        # First LSTM layer
        lstm1_out, _ = self.lstm1(x)
        lstm1_out = self.dropout1(lstm1_out)
        
        # Second LSTM layer
        lstm2_out, _ = self.lstm2(lstm1_out)
        lstm2_out = self.dropout2(lstm2_out)
        
        # Take the last output
        last_output = lstm2_out[:, -1, :]
        
        # Fully connected layers
        fc1_out = self.relu(self.fc1(last_output))
        fc1_out = self.dropout3(fc1_out)
        output = self.fc2(fc1_out)
        
        return output

def load_and_label_data(data_dir="data/series"):
    """Load all CSV files and create labels based on filename."""
    all_data = []
    all_labels = []
    
    # Get all CSV files
    csv_files = glob.glob(os.path.join(data_dir, "*.csv"))
    print(f"Found {len(csv_files)} CSV files")
    
    # Count files by type
    brushing_count = 0
    flossing_count = 0
    misc_count = 0
    skipped_count = 0
    
    for file_path in tqdm(csv_files, desc="Loading data"):
        filename = os.path.basename(file_path)
        
        # Determine label from filename
        if "brushing" in filename:
            label = "brushing"
            brushing_count += 1
        elif "flossing" in filename:
            label = "flossing"
            flossing_count += 1
        else:  # misc files
            label = "no_action"
            misc_count += 1
        
        # Load CSV
        df = pd.read_csv(file_path)
        
        # Skip if too short
        if len(df) < SEQUENCE_LENGTH:
            print(f"Skipping {filename}: only {len(df)} rows (need {SEQUENCE_LENGTH})")
            skipped_count += 1
            continue
            
        all_data.append(df.values)
        all_labels.append(label)  # One label per file, not per row
    
    print(f"Loaded files: {brushing_count} brushing, {flossing_count} flossing, {misc_count} misc")
    print(f"Skipped {skipped_count} files (too short)")
    
    return all_data, all_labels

def create_sequences(data, labels, sequence_length=SEQUENCE_LENGTH):
    """Create sequences from the data."""
    X, y = [], []
    
    for df_data, label in zip(data, labels):
        # Create sliding windows
        for i in range(len(df_data) - sequence_length + 1):
            sequence = df_data[i:i + sequence_length]
            X.append(sequence)
            y.append(label)
    
    return np.array(X), np.array(y)

def train_model(model, train_loader, val_loader, num_epochs=EPOCHS):
    """Train the model."""
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)
    
    best_val_loss = float('inf')
    patience_counter = 0
    patience = 10
    
    for epoch in range(num_epochs):
        # Training
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0
        
        for sequences, labels in tqdm(train_loader, desc=f"Epoch {epoch+1}/{num_epochs}"):
            sequences, labels = sequences.to(DEVICE), labels.to(DEVICE)
            
            optimizer.zero_grad()
            outputs = model(sequences)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            train_total += labels.size(0)
            train_correct += (predicted == labels).sum().item()
        
        # Validation
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        
        with torch.no_grad():
            for sequences, labels in val_loader:
                sequences, labels = sequences.to(DEVICE), labels.to(DEVICE)
                outputs = model(sequences)
                loss = criterion(outputs, labels)
                
                val_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()
        
        # Calculate metrics
        train_acc = 100 * train_correct / train_total
        val_acc = 100 * val_correct / val_total
        avg_train_loss = train_loss / len(train_loader)
        avg_val_loss = val_loss / len(val_loader)
        
        print(f"Epoch {epoch+1}/{num_epochs}:")
        print(f"  Train Loss: {avg_train_loss:.4f}, Train Acc: {train_acc:.2f}%")
        print(f"  Val Loss: {avg_val_loss:.4f}, Val Acc: {val_acc:.2f}%")
        
        # Learning rate scheduling
        scheduler.step(avg_val_loss)
        
        # Early stopping
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            patience_counter = 0
            # Save best model
            torch.save(model.state_dict(), "models/best_model.pth")
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"Early stopping at epoch {epoch+1}")
                break
    
    # Load best model
    model.load_state_dict(torch.load("models/best_model.pth"))
    return model

def evaluate_model(model, test_loader, label_encoder):
    """Evaluate the model and print detailed results."""
    model.eval()
    all_predictions = []
    all_labels = []
    
    with torch.no_grad():
        for sequences, labels in test_loader:
            sequences, labels = sequences.to(DEVICE), labels.to(DEVICE)
            outputs = model(sequences)
            _, predicted = torch.max(outputs, 1)
            
            all_predictions.extend(predicted.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
    
    # Convert back to class names
    predicted_classes = label_encoder.inverse_transform(all_predictions)
    true_classes = label_encoder.inverse_transform(all_labels)
    
    print("\nClassification Report:")
    print(classification_report(true_classes, predicted_classes))
    
    print("\nConfusion Matrix:")
    print(confusion_matrix(true_classes, predicted_classes))
    
    # Calculate accuracy
    accuracy = (np.array(all_predictions) == np.array(all_labels)).mean()
    print(f"\nTest Accuracy: {accuracy:.4f}")
    
    return accuracy

def main():
    print(f"Using device: {DEVICE}")
    print("Loading and preprocessing data...")
    
    # Load data
    all_data, labels = load_and_label_data()
    
    if not all_data:
        print("No data found! Make sure you have CSV files in data/series/")
        return
    
    print(f"Loaded {len(all_data)} video sequences")
    print(f"Total frames: {sum(len(data) for data in all_data)}")
    
    # Create sequences
    X, y = create_sequences(all_data, labels)
    print(f"Created {len(X)} sequences of length {SEQUENCE_LENGTH}")
    
    # Encode labels
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)
    
    print(f"Classes: {label_encoder.classes_}")
    print(f"Class distribution: {np.bincount(y_encoded)}")
    
    # Normalize features
    scaler = StandardScaler()
    X_reshaped = X.reshape(-1, X.shape[-1])
    X_scaled = scaler.fit_transform(X_reshaped)
    X_scaled = X_scaled.reshape(X.shape)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
    )
    
    # Further split training into train/val
    X_train, X_val, y_train, y_val = train_test_split(
        X_train, y_train, test_size=0.2, random_state=42, stratify=y_train
    )
    
    print(f"Training set: {X_train.shape}")
    print(f"Validation set: {X_val.shape}")
    print(f"Test set: {X_test.shape}")
    
    # Create datasets and dataloaders
    train_dataset = LandmarkDataset(X_train, y_train)
    val_dataset = LandmarkDataset(X_val, y_val)
    test_dataset = LandmarkDataset(X_test, y_test)
    
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)
    
    # Build model
    input_size = X_train.shape[2]
    num_classes = len(label_encoder.classes_)
    
    model = TinyLSTM(input_size, num_classes=num_classes).to(DEVICE)
    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
    
    # Train model
    print("Training model...")
    start_time = time.time()
    model = train_model(model, train_loader, val_loader)
    training_time = time.time() - start_time
    print(f"Training completed in {training_time:.2f} seconds")
    
    # Evaluate
    print("Evaluating model...")
    test_accuracy = evaluate_model(model, test_loader, label_encoder)
    
    # Save model and preprocessors
    print("Saving model and preprocessors...")
    torch.save(model.state_dict(), "models/action_recognition_model.pth")
    
    with open("models/label_encoder.pkl", "wb") as f:
        pickle.dump(label_encoder, f)
    
    with open("models/scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)
    
    # Save model info
    model_info = {
        "sequence_length": SEQUENCE_LENGTH,
        "input_size": input_size,
        "num_classes": num_classes,
        "classes": label_encoder.classes_.tolist(),
        "test_accuracy": float(test_accuracy),
        "model_architecture": "TinyLSTM",
        "hidden_sizes": [16, 8]
    }
    
    with open("models/model_info.pkl", "wb") as f:
        pickle.dump(model_info, f)
    
    print("Training complete! Model saved to models/ directory")
    print(f"Final test accuracy: {test_accuracy:.4f}")

if __name__ == "__main__":
    # Create models directory
    os.makedirs("models", exist_ok=True)
    main()
