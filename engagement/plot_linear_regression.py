import pandas as pd
import matplotlib.pyplot as plt
import joblib
import os

def plot_linear_relationships():
    df = pd.read_csv("training_data.csv")
    model = joblib.load("linear_model.joblib")
    features = [
        "total_slide_time", "slides_opened_ratio", "first_attempt_accuracy",
        "overall_accuracy", "recall_fluency", "total_slides"
    ]
    output_dir = os.path.join(os.path.dirname(__file__), "static", "images")
    os.makedirs(output_dir, exist_ok=True)
    for i, feature in enumerate(features):
        plt.figure(figsize=(6, 4))
        X = df[feature].values.reshape(-1, 1)
        y = df["score"].values
        y_pred = model.intercept_ + model.coef_[i] * X
        plt.scatter(X, y, alpha=0.6, label="Actual")
        plt.plot(X, y_pred, color="red", label="Regression Line")
        plt.xlabel(feature)
        plt.ylabel("Score")
        plt.title(f"Linear Regression: {feature} vs. Score")
        plt.legend()
        plt.tight_layout()
        path = os.path.join(output_dir, f"linear_{feature}.png")
        plt.savefig(path)
        plt.close()

def plot_actual_vs_predicted():
    df = pd.read_csv("training_data.csv")
    model = joblib.load("linear_model.joblib")

    features = [
        "total_slide_time", "slides_opened_ratio", "first_attempt_accuracy",
        "overall_accuracy", "recall_fluency", "total_slides"
    ]
    X = df[features]
    y_actual = df["score"]
    y_pred = model.predict(X)

    plt.figure(figsize=(6, 6))
    plt.scatter(y_actual, y_pred, alpha=0.6, label="Predicted vs Actual")
    plt.plot([0, 3], [0, 3], color="red", linestyle="--", label="Perfect Prediction Line")
    plt.xlabel("Actual Score")
    plt.ylabel("Predicted Score")
    plt.title("Linear Regression: Actual vs Predicted")
    plt.legend()
    plt.tight_layout()

    output_path = os.path.join(os.path.dirname(__file__), "static", "images", "linear_actual_vs_pred.png")
    plt.savefig(output_path)
    plt.close()
