import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import joblib
import matplotlib.pyplot as plt
import os


def train_linear_model():
    # Step 1: Load the training data
    df = pd.read_csv("training_data.csv")
    print("Dataset shape:", df.shape)

    # Step 2: Select features and target
    features = [
        "total_slide_time", "slides_opened_ratio", "first_attempt_accuracy",
        "overall_accuracy", "recall_fluency", "total_slides"
    ]
    target = "score"

    X = df[features]
    y = df[target]

    # Step 3: Split the data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Step 4: Train Linear Regression model
    model = LinearRegression()
    model.fit(X_train, y_train)

    # Step 5: Predict and evaluate
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    # Step 6: Print results
    print("\nLinear Regression Evaluation:")
    print(f"Mean Squared Error (MSE): {mse:.2f}")
    print(f"R² Score: {r2:.2f}")
    print("Coefficients:")
    for name, coef in zip(features, model.coef_):
        print(f"  {name}: {coef:.4f}")
    print(f"Intercept: {model.intercept_:.2f}")

    # Step 7: Save model to disk
    joblib.dump(model, "linear_model.joblib")
    print("Model saved as linear_model.joblib")

    # Step 8: Generate and save plots
    plot_linear_visuals(X, y, model, features, model.predict(X))

    # Step 9: Return coefficients
    return {feature: round(coef, 4) for feature, coef in zip(features, model.coef_)}

def plot_linear_visuals(X, y, model, features, y_pred):
    output_dir = os.path.join(os.path.dirname(__file__), "static", "images")
    os.makedirs(output_dir, exist_ok=True)

    # Feature vs. Score (regression line)
    for i, feature in enumerate(features):
        plt.figure(figsize=(6, 4))
        Xi = X[feature]
        plt.scatter(Xi, y, alpha=0.6, label="Actual")
        line = model.intercept_ + model.coef_[i] * Xi
        plt.plot(Xi, line, color="red", label="Regression Line")
        plt.xlabel(feature)
        plt.ylabel("Score")
        plt.title(f"{feature} vs. Score")
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f"linear_{feature}.png"))
        plt.close()

    # Actual vs Predicted
    plt.figure(figsize=(6, 6))
    plt.scatter(y, y_pred, alpha=0.6, label="Predicted vs Actual")
    plt.plot([0, 3], [0, 3], color="red", linestyle="--", label="Ideal Fit Line")
    plt.xlabel("Actual Score")
    plt.ylabel("Predicted Score")
    plt.title("Actual vs Predicted (Linear Regression)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "linear_actual_vs_pred.png"))
    plt.close()