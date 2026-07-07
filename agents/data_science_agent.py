"""
Agent: data_science_agent
-------------------------
A Machine Learning Agent. Uses pandas and scikit-learn to train predictive models on datasets.
"""

import os
import traceback

DESCRIPTION = (
    "The Data Scientist Agent. Use this to automatically train Machine Learning models on CSV datasets. "
    "It handles basic data cleaning, trains a Random Forest Classifier or Regressor, and returns performance metrics."
)

PARAMETERS = {
    "dataset_path": {
        "type": "string",
        "description": "Absolute path to the CSV dataset.",
        "required": True
    },
    "target_column": {
        "type": "string",
        "description": "The name of the column you want to predict.",
        "required": True
    },
    "task_type": {
        "type": "string",
        "description": "The type of ML task: 'classification' or 'regression'.",
        "required": True
    }
}

def data_science_agent(dataset_path: str, target_column: str, task_type: str) -> dict:
    """Trains a basic ML model on the provided dataset."""
    if not os.path.exists(dataset_path):
        return {"error": f"Dataset not found at {dataset_path}"}
        
    try:
        import pandas as pd
        from sklearn.model_selection import train_test_split
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
        from sklearn.metrics import accuracy_score, classification_report, mean_squared_error, r2_score
        from sklearn.preprocessing import LabelEncoder
    except ImportError as e:
        return {
            "error": "setup required", 
            "message": f"Missing ML dependencies: {e}. Please install pandas and scikit-learn."
        }
        
    try:
        # 1. Load Data
        df = pd.read_csv(dataset_path)
        
        if target_column not in df.columns:
            return {"error": f"Target column '{target_column}' not found in dataset. Columns available: {list(df.columns)}"}
            
        # 2. Basic Cleaning (Drop NaNs for simplicity in this V1 agent)
        df = df.dropna()
        if len(df) < 10:
            return {"error": "Dataset has too few rows after dropping missing values."}
            
        # 3. Encode categorical variables
        le_dict = {}
        for col in df.columns:
            if df[col].dtype == 'object':
                le = LabelEncoder()
                df[col] = le.fit_transform(df[col].astype(str))
                le_dict[col] = le
                
        # 4. Split Data
        X = df.drop(columns=[target_column])
        y = df[target_column]
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # 5. Train and Evaluate
        if task_type == 'classification':
            model = RandomForestClassifier(n_estimators=100, random_state=42)
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            
            acc = accuracy_score(y_test, y_pred)
            report = classification_report(y_test, y_pred, output_dict=True)
            
            # Feature Importance
            importances = dict(zip(X.columns, model.feature_importances_))
            sorted_imp = {k: v for k, v in sorted(importances.items(), key=lambda item: item[1], reverse=True)}
            
            return {
                "success": True,
                "model": "RandomForestClassifier",
                "accuracy": acc,
                "classification_report": report,
                "top_features": list(sorted_imp.items())[:5]
            }
            
        elif task_type == 'regression':
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            # Feature Importance
            importances = dict(zip(X.columns, model.feature_importances_))
            sorted_imp = {k: v for k, v in sorted(importances.items(), key=lambda item: item[1], reverse=True)}
            
            return {
                "success": True,
                "model": "RandomForestRegressor",
                "mean_squared_error": mse,
                "r2_score": r2,
                "top_features": list(sorted_imp.items())[:5]
            }
            
        else:
            return {"error": f"Invalid task_type: {task_type}. Use 'classification' or 'regression'."}
            
    except Exception as e:
        return {"error": f"Failed to train model: {str(e)}", "traceback": traceback.format_exc()}
