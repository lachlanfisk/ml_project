import pandas as pd
from sklearn.tree import DecisionTreeRegressor, plot_tree, export_text
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import joblib
import os

def train_and_visualise_tree():
    df = pd.read_csv("training_data.csv")

    features = [
        "total_slide_time", "slides_opened_ratio", "first_attempt_accuracy",
        "overall_accuracy", "recall_fluency", "total_slides"
    ]
    target = "score"

    X = df[features]
    y = df[target]

    tree_model = DecisionTreeRegressor(max_depth=4, random_state=42)
    tree_model.fit(X, y)

    # Save the model
    joblib.dump(tree_model, "tree_model.joblib")

    # Plot the tree
    plt.figure(figsize=(20, 10))
    plot_tree(tree_model, feature_names=features, filled=True, rounded=True)
    plt.title("Decision Tree for Predicting Student Score")
    STATIC_IMAGE_PATH = os.path.join(os.path.dirname(__file__), "static", "images", "decision_tree.png")
    plt.savefig(STATIC_IMAGE_PATH)  
    plt.close()

    # Export rules as text
    rules = export_text(tree_model, feature_names=features)
    RULES_PATH = os.path.join(os.path.dirname(__file__), "static", "images", "tree_rules.txt")
    with open(RULES_PATH, "w") as f:
        f.write(rules)

    print("Tree trained, saved, and visualized.")
