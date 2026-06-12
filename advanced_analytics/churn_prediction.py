import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import LabelEncoder

BASE_DIR = os.path.dirname(os.path.abspath("__file__"))

EXPORT_TABLES_DIR = os.path.join(BASE_DIR, "exports", "tables")
EXPORT_VIZ_DIR = os.path.join(BASE_DIR, "exports", "visualizations")
os.makedirs(EXPORT_TABLES_DIR, exist_ok=True)
os.makedirs(EXPORT_VIZ_DIR, exist_ok=True)

plt.style.use("seaborn-v0_8-whitegrid")
sns.set_palette("husl")


def load_features() -> pd.DataFrame:
    ltv = pd.read_csv(os.path.join(EXPORT_TABLES_DIR, "customer_ltv.csv"))
    churn = pd.read_csv(os.path.join(
        EXPORT_TABLES_DIR, "customer_churn_risk.csv"))
    freq = pd.read_csv(os.path.join(EXPORT_TABLES_DIR,
                       "customer_rental_frequency.csv"))

    df = churn[["customer_id", "days_since_rental", "churn_risk"]].merge(
        ltv[["customer_id", "average_purchase_value", "purchase_frequency",
             "customer_lifespan", "clv"]],
        on="customer_id", how="inner"
    ).merge(
        freq[["customer_id", "rental_count", "payment_count", "return_rate"]],
        on="customer_id", how="inner"
    )

    return df


def build_churn_model() -> None:
    df = load_features()

    le = LabelEncoder()
    df["churn_label"] = le.fit_transform(df["churn_risk"])

    features = ["average_purchase_value", "purchase_frequency",
                "customer_lifespan", "clv", "rental_count", "payment_count", "return_rate"]

    X = df[features]
    y = df["churn_label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    lr = LogisticRegression(max_iter=1000, random_state=42)
    lr.fit(X_train, y_train)
    lr_preds = lr.predict(X_test)

    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X_train, y_train)
    rf_preds = rf.predict(X_test)

    print("\nLogistic Regression:")
    print(classification_report(y_test, lr_preds, target_names=le.classes_))

    print("\nRandom Forest:")
    print(classification_report(y_test, rf_preds, target_names=le.classes_))

    lr_cv = cross_val_score(lr, X, y, cv=5, scoring="accuracy")
    rf_cv = cross_val_score(rf, X, y, cv=5, scoring="accuracy")

    print(f"\nLogistic Regression CV scores: {lr_cv.round(4)}")
    print(f"Logistic Regression CV mean: {lr_cv.mean().round(4)}")

    print(f"\nRandom Forest CV scores: {rf_cv.round(4)}")
    print(f"Random Forest CV mean: {rf_cv.mean().round(4)}")

    lr_acc = (lr_preds == y_test).mean()
    rf_acc = (rf_preds == y_test).mean()
    best_preds = rf_preds if rf_acc >= lr_acc else lr_preds
    best_name = "random_forest" if rf_acc >= lr_acc else "logistic_regression"

    print(f"\nBest model: {best_name}")

    predictions = df.iloc[y_test.index][["customer_id", "churn_risk"]].copy()
    predictions["predicted_churn"] = le.inverse_transform(best_preds)
    predictions.to_csv(os.path.join(EXPORT_TABLES_DIR,
                       "churn_predictions.csv"), index=False)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    sns.heatmap(confusion_matrix(y_test, lr_preds), annot=True, fmt="d",
                xticklabels=le.classes_, yticklabels=le.classes_, ax=axes[0])
    axes[0].set_title("Logistic Regression Confusion Matrix",
                      fontsize=13, fontweight="bold")
    axes[0].set_xlabel("Predicted")
    axes[0].set_ylabel("Actual")

    sns.heatmap(confusion_matrix(y_test, rf_preds), annot=True, fmt="d",
                xticklabels=le.classes_, yticklabels=le.classes_, ax=axes[1])
    axes[1].set_title("Random Forest Confusion Matrix",
                      fontsize=13, fontweight="bold")
    axes[1].set_xlabel("Predicted")
    axes[1].set_ylabel("Actual")

    plt.tight_layout()
    plt.savefig(os.path.join(EXPORT_VIZ_DIR, "churn_confusion_matrices.png"),
                dpi=150, bbox_inches="tight")
    plt.close()

    importance = pd.DataFrame({
        "feature": features,
        "importance": rf.feature_importances_
    }).sort_values("importance", ascending=False)

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(data=importance, x="importance", y="feature", ax=ax)
    ax.set_title("Random Forest Feature Importance",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Importance")
    ax.set_ylabel("Feature")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(os.path.join(EXPORT_VIZ_DIR, "churn_feature_importance.png"),
                dpi=150, bbox_inches="tight")
    plt.close()

    cv_df = pd.DataFrame({
        "fold": [f"fold_{i+1}" for i in range(5)],
        "logistic_regression": lr_cv.round(4),
        "random_forest": rf_cv.round(4)
    })

    fig, ax = plt.subplots(figsize=(10, 5))
    x = range(len(cv_df))
    width = 0.35
    ax.bar([i - width/2 for i in x], cv_df["logistic_regression"],
           width, label="Logistic Regression")
    ax.bar([i + width/2 for i in x], cv_df["random_forest"],
           width, label="Random Forest")
    ax.set_xticks(list(x))
    ax.set_xticklabels(cv_df["fold"])
    ax.set_title("Cross-Validation Accuracy by Fold",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Fold")
    ax.set_ylabel("Accuracy")
    ax.legend()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(os.path.join(EXPORT_VIZ_DIR, "churn_cv_scores.png"),
                dpi=150, bbox_inches="tight")
    plt.close()
