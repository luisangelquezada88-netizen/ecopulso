"""Modelos de machine learning implementados desde cero con numpy/pandas.

Implementaciones ligeras y sin dependencias externas pesadas, pensadas para
funcionar en el entorno del dashboard (Quarto/Folium) donde no siempre se
puede instalar scikit-learn.

Modelos incluidos:
  - KMeans: clustering no supervisado (zonas climáticas, perfiles contaminantes)
  - Regresión lineal múltiple (gradiente descendente): predicción temperatura/caudal
  - RandomForestRegressor simplificado: bagging de árboles de decisión desde cero
  - IsolationForest simplificado: detección de anomalías (sequía/inundación, outliers aire)

Todos los modelos aceptan y devuelven pandas DataFrame/Series o numpy arrays.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


# ===========================================================================
# Utilidades numéricas
# ===========================================================================

def _estandardizar(X: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Devuelve X estandarizado, media y desviación estándar por columna."""
    mu = X.mean(axis=0)
    sigma = X.std(axis=0)
    sigma[sigma == 0] = 1.0
    return (X - mu) / sigma, mu, sigma


def _train_test_split(
    X: np.ndarray, y: np.ndarray, test_size: float = 0.2, seed: int = 42
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Split aleatorio simple sin sklearn."""
    rng = np.random.default_rng(seed)
    n = X.shape[0]
    idx = rng.permutation(n)
    n_test = int(n * test_size)
    test_idx = idx[:n_test]
    train_idx = idx[n_test:]
    return X[train_idx], X[test_idx], y[train_idx], y[test_idx]


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def r2_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    ss_res = float(np.sum((y_true - y_pred) ** 2))
    ss_tot = float(np.sum((y_true - y_true.mean()) ** 2))
    if ss_tot == 0:
        return 0.0
    return float(1 - ss_res / ss_tot)


# ===========================================================================
# K-Means (clustering no supervisado)
# ===========================================================================

class KMeans:
    """K-Means desde cero con inicialización k-means++."""

    def __init__(self, n_clusters: int = 3, max_iter: int = 300, seed: int = 42):
        self.n_clusters = n_clusters
        self.max_iter = max_iter
        self.seed = seed
        self.centroides: Optional[np.ndarray] = None
        self.labels_: Optional[np.ndarray] = None
        self.inercia_: Optional[float] = None

    def fit(self, X: np.ndarray) -> "KMeans":
        rng = np.random.default_rng(self.seed)
        n, d = X.shape

        # k-means++ inicialización
        centroides = np.empty((self.n_clusters, d))
        idx0 = rng.integers(0, n)
        centroides[0] = X[idx0]
        for k in range(1, self.n_clusters):
            dist2 = np.min(np.sum((X[:, None, :] - centroides[:k]) ** 2, axis=2), axis=1)
            probs = dist2 / dist2.sum()
            idx = rng.choice(n, p=probs)
            centroides[k] = X[idx]

        for _ in range(self.max_iter):
            # Asignar puntos al centroide más cercano
            dist2 = np.sum((X[:, None, :] - centroides[None, :, :]) ** 2, axis=2)
            labels = np.argmin(dist2, axis=1)

            # Recalcular centroides
            nuevos = np.empty_like(centroides)
            for k in range(self.n_clusters):
                if np.any(labels == k):
                    nuevos[k] = X[labels == k].mean(axis=0)
                else:
                    nuevos[k] = centroides[k]

            if np.allclose(nuevos, centroides):
                break
            centroides = nuevos

        self.centroides = centroides
        self.labels_ = labels
        dist2 = np.sum((X[:, None, :] - centroides[None, :, :]) ** 2, axis=2)
        self.inercia_ = float(np.sum(np.min(dist2, axis=1)))
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        assert self.centroides is not None
        dist2 = np.sum((X[:, None, :] - self.centroides[None, :, :]) ** 2, axis=2)
        return np.argmin(dist2, axis=1)


# ===========================================================================
# Regresión lineal múltiple (gradiente descendente)
# ===========================================================================

class RegresionLineal:
    """Regresión lineal múltiple con gradiente descendente y regularización opcional."""

    def __init__(
        self, learning_rate: float = 0.01, n_iter: int = 1000, l2: float = 0.0, seed: int = 42
    ):
        self.learning_rate = learning_rate
        self.n_iter = n_iter
        self.l2 = l2
        self.seed = seed
        self.coef_: Optional[np.ndarray] = None
        self.interseccion_: float = 0.0
        self.historial_p_: list[float] = []

    def fit(self, X: np.ndarray, y: np.ndarray) -> "RegresionLineal":
        Xs, self.mu_x_, self.sigma_x_ = _estandardizar(X)
        ys, self.mu_y_, self.sigma_y_ = _estandardizar(y.reshape(-1, 1))
        ys = ys.ravel()

        n, d = Xs.shape
        self.coef_ = np.zeros(d)
        self.interseccion_ = 0.0

        for _ in range(self.n_iter):
            pred = Xs @ self.coef_ + self.interseccion_
            error = pred - ys
            grad_coef = (Xs.T @ error) / n + (self.l2 / n) * self.coef_
            grad_ino = error.mean()
            self.coef_ -= self.learning_rate * grad_coef
            self.interseccion_ -= self.learning_rate * grad_ino
            mse = float(np.mean(error ** 2))
            self.historial_p_.append(mse)

        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        assert self.coef_ is not None
        Xs = (X - self.mu_x_) / self.sigma_x_
        pred_s = Xs @ self.coef_ + self.interseccion_
        return pred_s * self.sigma_y_ + self.mu_y_

    def score(self, X: np.ndarray, y: np.ndarray) -> float:
        return r2_score(y, self.predict(X))


# ===========================================================================
# Árbol de decisión simplificado (para Random Forest)
# ===========================================================================

class _NodoArbol:
    """Nodo de un árbol de decisión para regresión."""

    __slots__ = ("indice_feat", "umbral", "izq", "der", "valor")

    def __init__(self, indice_feat=None, umbral=None, izq=None, der=None, valor=None):
        self.indice_feat = indice_feat
        self.umbral = umbral
        self.izq = izq
        self.der = der
        self.valor = valor


class _ArbolRegresion:
    """Árbol de decisión para regresión (MSE como criterio de división)."""

    def __init__(self, max_depth: int = 5, min_samples_split: int = 5, seed: int = 42):
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.seed = seed
        self.raiz: Optional[_NodoArbol] = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "_ArbolRegresion":
        rng = np.random.default_rng(self.seed)
        self.raiz = self._construir(X, y, rng, profundidad=0)
        return self

    def _construir(
        self, X: np.ndarray, y: np.ndarray, rng: np.random.Generator, profundidad: int
    ) -> _NodoArbol:
        n = X.shape[0]
        valor = float(y.mean())

        if (
            profundidad >= self.max_depth
            or n < self.min_samples_split
            or len(np.unique(y)) == 1
        ):
            return _NodoArbol(valor=valor)

        mejor_ganancia = -np.inf
        mejor_split = None

        # Probar divisiones aleatorias sobre un subconjunto de features
        features = rng.choice(X.shape[1], size=min(X.shape[1], max(2, X.shape[1] // 2)), replace=False)
        for fi in features:
            umbrales = np.unique(X[:, fi])
            if len(umbrales) < 2:
                continue
            for t in umbrales[:: max(1, len(umbrales) // 10)]:
                izq_mask = X[:, fi] <= t
                der_mask = ~izq_mask
                if izq_mask.sum() == 0 or der_mask.sum() == 0:
                    continue
                ganancia = self._reduccion_varianza(y, y[izq_mask], y[der_mask])
                if ganancia > mejor_ganancia:
                    mejor_ganancia = ganancia
                    mejor_split = (fi, t)

        if mejor_split is None:
            return _NodoArbol(valor=valor)

        fi, t = mejor_split
        izq_mask = X[:, fi] <= t
        der_mask = ~izq_mask
        nodo = _NodoArbol(indice_feat=fi, umbral=t)
        nodo.izq = self._construir(X[izq_mask], y[izq_mask], rng, profundidad + 1)
        nodo.der = self._construir(X[der_mask], y[der_mask], rng, profundidad + 1)
        return nodo

    def _reduccion_varianza(self, y: np.ndarray, y_izq: np.ndarray, y_der: np.ndarray) -> float:
        n = len(y)
        var_padre = np.var(y)
        var_izq = np.var(y_izq) if len(y_izq) > 0 else 0
        var_der = np.var(y_der) if len(y_der) > 0 else 0
        ponderada = (len(y_izq) * var_izq + len(y_der) * var_der) / n
        return var_padre - ponderada

    def _predecir_fila(self, x: np.ndarray, nodo: _NodoArbol) -> float:
        if nodo.valor is not None:
            return nodo.valor
        if x[nodo.indice_feat] <= nodo.umbral:
            return self._predecir_fila(x, nodo.izq)
        return self._predecir_fila(x, nodo.der)

    def predict(self, X: np.ndarray) -> np.ndarray:
        assert self.raiz is not None
        return np.array([self._predecir_fila(x, self.raiz) for x in X])


# ===========================================================================
# Random Forest simplificado (bagging de árboles de decisión)
# ===========================================================================

class RandomForestRegressor:
    """Random Forest para regresión con bagging y submuestreo de features."""

    def __init__(
        self,
        n_arboles: int = 10,
        max_depth: int = 5,
        min_samples_split: int = 5,
        seed: int = 42,
    ):
        self.n_arboles = n_arboles
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.seed = seed
        self.arboles: list[_ArbolRegresion] = []

    def fit(self, X: np.ndarray, y: np.ndarray) -> "RandomForestRegressor":
        rng = np.random.default_rng(self.seed)
        n = X.shape[0]
        self.arboles = []
        for i in range(self.n_arboles):
            # Bootstrap sample
            idx = rng.integers(0, n, size=n)
            Xb = X[idx]
            yb = y[idx]
            arbol = _ArbolRegresion(
                max_depth=self.max_depth,
                min_samples_split=self.min_samples_split,
                seed=int(rng.integers(0, 1_000_000)),
            )
            arbol.fit(Xb, yb)
            self.arboles.append(arbol)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        preds = np.column_stack([a.predict(X) for a in self.arboles])
        return preds.mean(axis=1)

    def score(self, X: np.ndarray, y: np.ndarray) -> float:
        return r2_score(y, self.predict(X))


# ===========================================================================
# Isolation Forest simplificado (detección de anomalías)
# ===========================================================================

class IsolationForest:
    """Isolation Forest para detección de anomalías (puntuación de anomalía)."""

    def __init__(self, n_arboles: int = 50, max_depth: int = 10, seed: int = 42):
        self.n_arboles = n_arboles
        self.max_depth = max_depth
        self.seed = seed
        self.arboles: list = []
        self.umbral_anomalia_: Optional[float] = None

    def fit(self, X: np.ndarray) -> "IsolationForest":
        rng = np.random.default_rng(self.seed)
        self.arboles = []
        for _ in range(self.n_arboles):
            self.arboles.append(self._construir_arbol_aislamiento(X, rng))
        # Calcular umbral de anomalía (percentil 5 de puntuaciones)
        scores = np.array([self._puntuacion_anomalia(x) for x in X])
        self.umbral_anomalia_ = float(np.percentile(scores, 5))
        return self

    def _construir_arbol_aislamiento(self, X: np.ndarray, rng: np.random.Generator) -> dict:
        n = X.shape[0]
        if n <= 1 or self.max_depth == 0:
            return {"tipo": "hoja", "size": n}
        fi = rng.integers(0, X.shape[1])
        col = X[:, fi]
        if col.min() == col.max():
            return {"tipo": "hoja", "size": n}
        umbral = rng.uniform(col.min(), col.max())
        izq_mask = X[:, fi] <= umbral
        der_mask = ~izq_mask
        return {
            "tipo": "nodo",
            "feature": int(fi),
            "umbral": float(umbral),
            "izq": self._construir_arbol_aislamiento(X[izq_mask], rng) if np.any(izq_mask) else {"tipo": "hoja", "size": 0},
            "der": self._construir_arbol_aislamiento(X[der_mask], rng) if np.any(der_mask) else {"tipo": "hoja", "size": 0},
            "profundidad": self.max_depth - 1,
        }

    def _camino_longitud(self, x: np.ndarray, nodo: dict, profundidad: int = 0) -> float:
        if nodo["tipo"] == "hoja":
            return profundidad + (2.0 * np.log(max(nodo["size"], 2)) - 1.0) if nodo["size"] > 0 else profundidad
        if x[nodo["feature"]] <= nodo["umbral"]:
            return self._camino_longitud(x, nodo["izq"], profundidad + 1)
        return self._camino_longitud(x, nodo["der"], profundidad + 1)

    def _puntuacion_anomalia(self, x: np.ndarray) -> float:
        longitudes = [self._camino_longitud(x, a) for a in self.arboles]
        longitud_media = float(np.mean(longitudes))
        # Factor de normalización aproximado para tamaño de muestra
        c = 2.0 * np.log(max(len(self.arboles), 2)) - 1.0
        return float(2.0 ** (-longitud_media / c))

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Devuelve -1 para anomalía, 1 para normal."""
        scores = np.array([self._puntuacion_anomalia(x) for x in X])
        assert self.umbral_anomalia_ is not None
        return np.where(scores < self.umbral_anomalia_, -1, 1)

    def decision_function(self, X: np.ndarray) -> np.ndarray:
        return np.array([self._puntuacion_anomalia(x) for x in X])


# ===========================================================================
# Funciones de conveniencia para el dashboard
# ===========================================================================

def preparar_matriz(df: pd.DataFrame, columnas: list[str], objetivo: str) -> tuple[np.ndarray, np.ndarray]:
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
        "r2": r2_score(y_test, y_pred),
        "n_test": len(y_test),
    }


def kmeans_desde_dataframe(
    df: pd.DataFrame, columnas: list[str], n_clusters: int = 3, seed: int = 42
) -> tuple[pd.DataFrame, KMeans]:
    """Aplica K-Means a un DataFrame y devuelve el DataFrame con columna 'cluster'."""
    sub = df[columnas].dropna()
    X = sub[columnas].values.astype(float)
    km = KMeans(n_clusters=n_clusters, seed=seed)
    km.fit(X)
    sub = sub.copy()
    sub["cluster"] = km.predict(X)
    return sub, km
