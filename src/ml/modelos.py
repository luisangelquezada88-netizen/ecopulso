"""Modelos de machine learning con scikit-learn (stack permanente del proyecto).

Backend: scikit-learn + numpy + pandas.
Modelos incluidos:
  - KMeans: clustering no supervisado (zonas climáticas, perfiles contaminantes)
  - RandomForestClassifier: clasificación (categoría OMS aire)
  - RandomForestRegressor: predicción (temperatura, caudal)
  - IsolationForest: detección de anomalías (sequía/inundación, outliers aire)
  - Regresión lineal (LinearRegression / SGDRegressor): baseline interpretable

Todas las funciones aceptan y devuelven pandas DataFrame/Series o numpy arrays.
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans as SKLearnKMeans
from sklearn.ensemble import (
    IsolationForest as SKLearnIsolationForest,
    RandomForestClassifier as SKLearnRandomForestClassifier,
    RandomForestRegressor as SKLearnRandomForestRegressor,
)
from sklearn.linear_model import LinearRegression, SGDRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    confusion_matrix,
    r2_score,
    mean_squared_error,
    mean_absolute_error,
)


# ===========================================================================
# Utilidades numéricas
# ===========================================================================

def _estandardizar(X: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Devuelve X estandarizado, media y desviación estándar por columna."""
    mu = X.mean(axis=0)
    sigma = X.std(axis=0)
    sigma[sigma == 0] = 1.0
    return (X - mu) / sigma, mu, sigma


def _train_test_split(
    X: np.ndarray, y: np.ndarray, test_size: float = 0.2, seed: int = 42, stratify=None
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Split aleatorio simple con scikit-learn."""
    return train_test_split(X, y, test_size=test_size, random_state=seed, stratify=stratify)


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(mean_absolute_error(y_true, y_pred))


def r2_score_sk(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(r2_score(y_true, y_pred))


# ===========================================================================
# K-Means (clustering no supervisado)
# ===========================================================================

class KMeans:
    """Wrapper de scikit-learn KMeans con interfaz simplificada."""

    def __init__(self, n_clusters: int = 3, max_iter: int = 300, seed: int = 42):
        self.n_clusters = n_clusters
        self.max_iter = max_iter
        self.seed = seed
        self.modelo: Optional[SKLearnKMeans] = None
        self.centroides: Optional[np.ndarray] = None
        self.labels_: Optional[np.ndarray] = None
        self.inercia_: Optional[float] = None

    def fit(self, X: np.ndarray) -> "KMeans":
        self.modelo = SKLearnKMeans(
            n_clusters=self.n_clusters,
            max_iter=self.max_iter,
            random_state=self.seed,
            n_init=10,
        )
        self.modelo.fit(X)
        self.centroides = self.modelo.cluster_centers_
        self.labels_ = self.modelo.labels_
        self.inercia_ = float(self.modelo.inertia_)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        assert self.modelo is not None
        return self.modelo.predict(X)


# ===========================================================================
# Regresión lineal múltiple (scikit-learn)
# ===========================================================================

class RegresionLineal:
    """Regresión lineal con scikit-learn (LinearRegression o SGD para datasets grandes)."""

    def __init__(
        self, learning_rate: float = 0.01, n_iter: int = 1000, l2: float = 0.0, seed: int = 42
    ):
        self.learning_rate = learning_rate
        self.n_iter = n_iter
        self.l2 = l2
        self.seed = seed
        self.modelo: Optional[LinearRegression | SGDRegressor] = None
        self.mu_x_: Optional[np.ndarray] = None
        self.sigma_x_: Optional[np.ndarray] = None
        self.mu_y_: float = 0.0
        self.sigma_y_: float = 1.0
        self.historial_p_: list[float] = []

    def fit(self, X: np.ndarray, y: np.ndarray) -> "RegresionLineal":
        # Estandarizar para mejor convergencia
        Xs, self.mu_x_, self.sigma_x_ = _estandardizar(X)
        ys_2d = y.reshape(-1, 1)
        ys, self.mu_y_, self.sigma_y_ = _estandardizar(ys_2d)
        ys = ys.ravel()

        # Usar LinearRegression (exacto) si hay pocos datos, SGD si son muchos
        if X.shape[0] < 5000:
            self.modelo = LinearRegression()
            self.modelo.fit(Xs, ys)
            y_pred_train = self.modelo.predict(Xs)
            self.historial_p_ = [float(mean_squared_error(ys, y_pred_train))]
        else:
            self.modelo = SGDRegressor(
                learning_rate="constant",
                eta0=self.learning_rate,
                max_iter=self.n_iter,
                alpha=self.l2,
                random_state=self.seed,
            )
            self.modelo.fit(Xs, ys)
            y_pred_train = self.modelo.predict(Xs)
            self.historial_p_ = [float(mean_squared_error(ys, y_pred_train))]

        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        assert self.modelo is not None
        assert self.mu_x_ is not None and self.sigma_x_ is not None
        Xs = (X - self.mu_x_) / self.sigma_x_
        pred_s = self.modelo.predict(Xs)
        return pred_s * self.sigma_y_ + self.mu_y_

    def score(self, X: np.ndarray, y: np.ndarray) -> float:
        return r2_score_sk(y, self.predict(X))


# ===========================================================================
# Random Forest (scikit-learn)
# ===========================================================================

class RandomForestRegressor:
    """Wrapper de scikit-learn RandomForestRegressor."""

    def __init__(
        self,
        n_arboles: int = 100,
        max_depth: Optional[int] = None,
        min_samples_split: int = 2,
        seed: int = 42,
    ):
        self.n_arboles = n_arboles
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.seed = seed
        self.modelo: Optional[SKLearnRandomForestRegressor] = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "RandomForestRegressor":
        self.modelo = SKLearnRandomForestRegressor(
            n_estimators=self.n_arboles,
            max_depth=self.max_depth,
            min_samples_split=self.min_samples_split,
            random_state=self.seed,
            n_jobs=-1,
        )
        self.modelo.fit(X, y)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        assert self.modelo is not None
        return self.modelo.predict(X)

    def score(self, X: np.ndarray, y: np.ndarray) -> float:
        assert self.modelo is not None
        return float(self.modelo.score(X, y))

    def feature_importances_(self) -> Optional[np.ndarray]:
        assert self.modelo is not None
        return self.modelo.feature_importances_


class RandomForestClassifier:
    """Wrapper de scikit-learn RandomForestClassifier."""

    def __init__(
        self,
        n_arboles: int = 100,
        max_depth: Optional[int] = None,
        min_samples_split: int = 2,
        seed: int = 42,
        class_weight=None,
    ):
        self.n_arboles = n_arboles
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.seed = seed
        self.class_weight = class_weight
        self.modelo: Optional[SKLearnRandomForestClassifier] = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "RandomForestClassifier":
        self.modelo = SKLearnRandomForestClassifier(
            n_estimators=self.n_arboles,
            max_depth=self.max_depth,
            min_samples_split=self.min_samples_split,
            random_state=self.seed,
            class_weight=self.class_weight,
            n_jobs=-1,
        )
        self.modelo.fit(X, y)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        assert self.modelo is not None
        return self.modelo.predict(X)

    def score(self, X: np.ndarray, y: np.ndarray) -> float:
        assert self.modelo is not None
        return float(self.modelo.score(X, y))

    def feature_importances_(self) -> Optional[np.ndarray]:
        assert self.modelo is not None
        return self.modelo.feature_importances_


# ===========================================================================
# Isolation Forest (scikit-learn)
# ===========================================================================

class IsolationForest:
    """Wrapper de scikit-learn IsolationForest.

    Nota: sklearn no expone ``max_depth`` en IsolationForest; se acepta el
    parámetro por compatibilidad de interfaz pero se ignora.
    """

    def __init__(self, n_arboles: int = 100, max_depth: Optional[int] = None, seed: int = 42):
        self.n_arboles = n_arboles
        self.max_depth = max_depth  # no soportado por sklearn; se mantiene por API
        self.seed = seed
        self.modelo: Optional[SKLearnIsolationForest] = None
        self.umbral_anomalia_: Optional[float] = None

    def fit(self, X: np.ndarray) -> "IsolationForest":
        self.modelo = SKLearnIsolationForest(
            n_estimators=self.n_arboles,
            max_samples="auto",
            contamination="auto",
            max_features=1.0,
            bootstrap=False,
            n_jobs=-1,
            random_state=self.seed,
        )
        self.modelo.fit(X)
        # Umbral: percentil 5 de los scores de decisión sobre X de entrenamiento
        scores = self.modelo.decision_function(X)
        self.umbral_anomalia_ = float(np.percentile(scores, 5))
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Devuelve -1 para anomalía, 1 para normal."""
        assert self.modelo is not None
        return self.modelo.predict(X)

    def decision_function(self, X: np.ndarray) -> np.ndarray:
        assert self.modelo is not None
        return self.modelo.decision_function(X)


# ===========================================================================
# Funciones de conveniencia para el dashboard
# ===========================================================================

def preparar_matriz(df: pd.DataFrame, columnas: list[str], objetivo: str) -> Tuple[np.ndarray, np.ndarray]:
    """Extrae X e y de un DataFrame eliminando filas con nulos."""
    sub = df[columnas + [objetivo]].dropna()
    X = sub[columnas].values.astype(float)
    y = sub[objetivo].values.astype(float)
    return X, y


def evaluar_modelo_regresion(modelo, X_test: np.ndarray, y_test: np.ndarray) -> dict:
    """Devuelve métricas de regresión para un modelo entrenado."""
    y_pred = modelo.predict(X_test)
    return {
        "rmse": rmse(y_test, y_pred),
        "mae": mae(y_test, y_pred),
        "r2": r2_score_sk(y_test, y_pred),
        "n_test": len(y_test),
    }


def kmeans_desde_dataframe(
    df: pd.DataFrame, columnas: list[str], n_clusters: int = 3, seed: int = 42
) -> Tuple[pd.DataFrame, KMeans]:
    """Aplica K-Means a un DataFrame y devuelve el DataFrame con columna 'cluster'."""
    sub = df[columnas].dropna()
    X = sub[columnas].values.astype(float)
    km = KMeans(n_clusters=n_clusters, seed=seed)
    km.fit(X)
    sub = sub.copy()
    sub["cluster"] = km.predict(X)
    return sub, km
