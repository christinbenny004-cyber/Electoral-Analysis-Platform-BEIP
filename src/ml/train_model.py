import sys
from pathlib import Path
import pandas as pd
from sqlalchemy import text
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.metrics import accuracy_score, precision_score, recall_score, classification_report
import joblib

# Add project root to path so we can import config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import get_engine

def load_data():
    """Load gold features from the database."""
    engine = get_engine()
    query = "SELECT * FROM gold.candidate_features;"
    df = pd.read_sql(query, engine)
    print(f"[LOAD] Loaded {len(df):,} candidate features from Gold layer.")
    return df

def train_and_evaluate(df):
    """Train the model and print evaluation metrics."""
    # Handle potentially missing Target rows if any
    df = df.dropna(subset=['won'])
    
    # 1. Feature Definition
    # We drop identifiers and only keep predictive features
    categorical_features = ['party', 'education']
    numeric_features = [
        'criminal_cases', 'serious_criminal_cases', 'total_assets', 'total_liabilities',
        'total_population', 'literacy_rate', 'sex_ratio', 'sc_percentage', 'st_percentage',
        'worker_participation', 'electors', 'turnout_percentage', 'total_candidates'
    ]
    
    X = df[categorical_features + numeric_features]
    y = df['won']

    print(f"[PREPROCESS] Features used: {len(X.columns)}")
    print(f"[PREPROCESS] Class distribution (Won=1, Lost=0):\n{y.value_counts(normalize=True)}")

    # 2. Build Preprocessing Pipeline
    # Numeric pipeline: Impute missing values with median, then scale
    numeric_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])

    # Categorical pipeline: Impute missing with 'Unknown', then One-Hot encode
    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='constant', fill_value='Unknown')),
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, numeric_features),
            ('cat', categorical_transformer, categorical_features)
        ])

    # 3. Build Full Pipeline with Classifier
    model = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('classifier', RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced'))
    ])

    # 4. Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    print(f"[TRAIN] Training set size: {len(X_train):,}, Test set size: {len(X_test):,}")

    # 5. Train Model
    print("[TRAIN] Fitting Random Forest model...")
    model.fit(X_train, y_train)

    # 6. Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    
    print("\n" + "="*40)
    print("MODEL EVALUATION METRICS")
    print("="*40)
    print(f"Accuracy : {accuracy:.4f} (Overall correctness)")
    print(f"Precision: {precision:.4f} (When it predicts a win, is it correct?)")
    print(f"Recall   : {recall:.4f} (Of all true winners, how many did it catch?)")
    print("\nFull Classification Report:")
    print(classification_report(y_test, y_pred))

    # 7. Extract Feature Importances (Optional but helpful for EDA)
    # The preprocessor generates new one-hot columns and might drop all-null numeric columns.
    num_feature_names = model.named_steps['preprocessor'].named_transformers_['num'].get_feature_names_out(numeric_features)
    cat_feature_names = model.named_steps['preprocessor'].named_transformers_['cat'].get_feature_names_out(categorical_features)
    all_feature_names = list(num_feature_names) + list(cat_feature_names)
    
    importances = model.named_steps['classifier'].feature_importances_
    feat_imp = pd.DataFrame({'Feature': all_feature_names, 'Importance': importances})
    feat_imp = feat_imp.sort_values(by='Importance', ascending=False).head(10)
    
    print("\n" + "="*40)
    print("TOP 10 MOST IMPORTANT FEATURES")
    print("="*40)
    print(feat_imp.to_string(index=False))

    return model

def save_model(model):
    """Save the trained model to disk."""
    model_dir = Path(__file__).resolve().parent.parent.parent / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "election_predictor.pkl"
    
    joblib.dump(model, model_path)
    print(f"\n[SAVE] Model successfully saved to {model_path}")

if __name__ == "__main__":
    print("="*60)
    print("BEIP -- Phase 2.2 Model Training")
    print("="*60)
    
    df = load_data()
    model = train_and_evaluate(df)
    save_model(model)
