import optuna
import mlflow
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score
from sklearn.metrics import f1_score
import json
import os

from sklearn.ensemble import RandomForestClassifier
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from optuna.visualization import plot_param_importances
from src.mlflow_tracking.artifact_logger import log_artifact_to_mlflow


def optimize_model_with_optuna(
    model_class, 
    param_distributions, 
    X_train, 
    y_train, 
    X_test, 
    y_test, 
    n_trials,
    metric=f1_score
):
    """
    Optimiza un modelo usando Optuna y registra los resultados en MLFlow.

    Args:
        model_class: Clase del modelo (e.g., RandomForestClassifier, XGBClassifier).
        param_distributions (dict): Diccionario de distribuciones de parámetros a optimizar.
        X_train, y_train: Datos de entrenamiento.
        X_test, y_test: Datos de prueba.
        n_trials (int): Número de trials para Optuna.
        metric (callable): Métrica de evaluación para optimizar (por defecto: f1_score).

    Returns:
        study: Objeto de estudio 
    """
    def objective(trial):
        # hiperparametros sugeridos
        params = {key: trial._suggest(key, value) for key, value in param_distributions.items()}

        #model_type = get_model_class(model_class)

        # se crea la instancia del modelo con los parametros 
        model = model_class.set_params(**params, random_state=42)

        pipeline = Pipeline([
        # ('preprocessor', preprocessor),  
            ('classifier', model)
        ])

        # validacion cruzada para calcular el f1-score
        score = cross_val_score(pipeline, X_train, y_train, n_jobs=-1, cv=3, scoring='f1_weighted').mean()
        return score
    
    # ahora se crea un estudio para maximizar el f1-score
    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=n_trials)  

    with mlflow.start_run(run_name=f"{str(model_class)} Optimization"):
        # Mejor trial
        best_trial = study.best_trial

        # Registrar hiperparámetros y métrica
        mlflow.log_params(best_trial.params)
        mlflow.log_metric("best_value", best_trial.value)
        with open("columns.json", "w") as f:
            json.dump(list(X_train.columns), f)
        mlflow.log_artifact("columns.json", artifact_path="model_metadata")

        fig = plot_param_importances(study)
        artifact_name = f"prediction_vs_real_{type(best_trial)}.png"
        temp_file = f"temp_{artifact_name}"
        fig.write_image(temp_file)
        mlflow.log_artifact(temp_file, artifact_path="plots")
        os.remove(temp_file)

        print("Estudio de Optuna registrado en MLFlow.")

    return study





