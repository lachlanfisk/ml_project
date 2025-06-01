import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import joblib

def train_model():
    # Step 1: Load the data
    df = pd.read_csv("training_data.csv")
    print("Dataset shape:", df.shape)

    # Step 2: Define features and target
    features = [
        "total_slide_time", "slides_opened_ratio", "first_attempt_accuracy",
        "overall_accuracy", "recall_fluency", "total_slides"
    ]
    target = "score"

    X = df[features]
    y = df[target]

    # Step 3: Split the dataset
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Step 4: Train the model
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # Step 5: Return feature importances
    importances = model.feature_importances_

    # Step 6: Make predictions
    y_pred = model.predict(X_test)

    # Step 7: Evaluate the model
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    # Step 8: Print the evaluation results
    print("\nEvaluation:")
    print(f"Mean Squared Error (MSE): {mse:.2f}")
    print(f"R² Score: {r2:.2f}")

    # Step 9: Save the trained model to disk
    joblib.dump(model, "ml_model.joblib")
    print("\nModel saved as ml_model.joblib")

    return {feature: round(importance, 4) for feature, importance in zip(features, importances)}
