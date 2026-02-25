use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};

use memori_core::{Memori, Memory, SearchQuery};
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

fn memori_err(e: memori_core::MemoriError) -> PyErr {
    PyRuntimeError::new_err(e.to_string())
}

fn py_value(py: Python<'_>, val: &serde_json::Value) -> PyResult<PyObject> {
    match val {
        serde_json::Value::Null => Ok(py.None()),
        serde_json::Value::Bool(b) => Ok(b.to_object(py)),
        serde_json::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                Ok(i.to_object(py))
            } else {
                Ok(n.as_f64().unwrap().to_object(py))
            }
        }
        serde_json::Value::String(s) => Ok(s.to_object(py)),
        serde_json::Value::Array(arr) => {
            let items: PyResult<Vec<PyObject>> = arr.iter().map(|v| py_value(py, v)).collect();
            Ok(PyList::new_bound(py, items?).to_object(py))
        }
        serde_json::Value::Object(map) => {
            let dict = PyDict::new_bound(py);
            for (k, v) in map {
                dict.set_item(k, py_value(py, v)?)?;
            }
            Ok(dict.to_object(py))
        }
    }
}

fn pydict_to_value(dict: &Bound<'_, PyDict>) -> PyResult<serde_json::Value> {
    let mut map = serde_json::Map::new();
    for (key, val) in dict.iter() {
        let k: String = key.extract()?;
        let v = pyobj_to_value(&val)?;
        map.insert(k, v);
    }
    Ok(serde_json::Value::Object(map))
}

fn pyobj_to_value(obj: &Bound<'_, PyAny>) -> PyResult<serde_json::Value> {
    if obj.is_none() {
        Ok(serde_json::Value::Null)
    } else if let Ok(b) = obj.extract::<bool>() {
        Ok(serde_json::Value::Bool(b))
    } else if let Ok(i) = obj.extract::<i64>() {
        Ok(serde_json::Value::Number(i.into()))
    } else if let Ok(f) = obj.extract::<f64>() {
        Ok(serde_json::Number::from_f64(f)
            .map(serde_json::Value::Number)
            .unwrap_or(serde_json::Value::Null))
    } else if let Ok(s) = obj.extract::<String>() {
        Ok(serde_json::Value::String(s))
    } else if let Ok(dict) = obj.downcast::<PyDict>() {
        pydict_to_value(dict)
    } else if let Ok(list) = obj.downcast::<PyList>() {
        let items: PyResult<Vec<_>> = list.iter().map(|item| pyobj_to_value(&item)).collect();
        Ok(serde_json::Value::Array(items?))
    } else {
        let s = obj.str()?.extract::<String>()?;
        Ok(serde_json::Value::String(s))
    }
}

fn memory_to_dict(py: Python<'_>, mem: &Memory) -> PyResult<PyObject> {
    let dict = PyDict::new_bound(py);
    dict.set_item("id", &mem.id)?;
    dict.set_item("content", &mem.content)?;
    dict.set_item("created_at", mem.created_at)?;
    dict.set_item("updated_at", mem.updated_at)?;

    match &mem.vector {
        Some(v) => dict.set_item("vector", v.to_object(py))?,
        None => dict.set_item("vector", py.None())?,
    }

    match &mem.metadata {
        Some(v) => dict.set_item("metadata", py_value(py, v)?)?,
        None => dict.set_item("metadata", py.None())?,
    }

    match mem.score {
        Some(s) => dict.set_item("score", s)?,
        None => dict.set_item("score", py.None())?,
    }

    Ok(dict.to_object(py))
}

#[pyclass]
struct PyMemori {
    inner: Mutex<Memori>,
}

#[pymethods]
impl PyMemori {
    #[new]
    fn new(path: &str) -> PyResult<Self> {
        let inner = Memori::open(path).map_err(memori_err)?;
        Ok(Self {
            inner: Mutex::new(inner),
        })
    }

    #[pyo3(signature = (content, vector=None, metadata=None))]
    fn insert(
        &self,
        content: &str,
        vector: Option<Vec<f32>>,
        metadata: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<String> {
        let meta = metadata.map(pydict_to_value).transpose()?;
        self.inner
            .lock()
            .unwrap()
            .insert(content, vector.as_deref(), meta)
            .map_err(memori_err)
    }

    fn get(&self, py: Python<'_>, id: &str) -> PyResult<Option<PyObject>> {
        let mem = self.inner.lock().unwrap().get(id).map_err(memori_err)?;
        match mem {
            Some(m) => Ok(Some(memory_to_dict(py, &m)?)),
            None => Ok(None),
        }
    }

    #[pyo3(signature = (id, content=None, vector=None, metadata=None))]
    fn update(
        &self,
        id: &str,
        content: Option<&str>,
        vector: Option<Vec<f32>>,
        metadata: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<()> {
        let meta = metadata.map(pydict_to_value).transpose()?;
        self.inner
            .lock()
            .unwrap()
            .update(id, content, vector.as_deref(), meta)
            .map_err(memori_err)
    }

    fn delete(&self, id: &str) -> PyResult<()> {
        self.inner.lock().unwrap().delete(id).map_err(memori_err)
    }

    #[pyo3(signature = (vector=None, text=None, filter=None, limit=10))]
    fn search(
        &self,
        py: Python<'_>,
        vector: Option<Vec<f32>>,
        text: Option<String>,
        filter: Option<&Bound<'_, PyDict>>,
        limit: usize,
    ) -> PyResult<Vec<PyObject>> {
        let filter_val = filter.map(pydict_to_value).transpose()?;
        let query = SearchQuery {
            vector,
            text,
            filter: filter_val,
            limit,
        };

        let results = py.allow_threads(|| {
            self.inner.lock().unwrap().search(query).map_err(memori_err)
        })?;

        results.iter().map(|m| memory_to_dict(py, m)).collect()
    }

    fn count(&self) -> PyResult<usize> {
        self.inner.lock().unwrap().count().map_err(memori_err)
    }

    #[pyo3(signature = (id, content, vector=None, metadata=None, created_at=None, updated_at=None))]
    fn insert_with_id(
        &self,
        id: &str,
        content: &str,
        vector: Option<Vec<f32>>,
        metadata: Option<&Bound<'_, PyDict>>,
        created_at: Option<f64>,
        updated_at: Option<f64>,
    ) -> PyResult<String> {
        let meta = metadata.map(pydict_to_value).transpose()?;
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs_f64();
        let ca = created_at.unwrap_or(now);
        let ua = updated_at.unwrap_or(now);
        self.inner
            .lock()
            .unwrap()
            .insert_with_id(id, content, vector.as_deref(), meta, ca, ua)
            .map_err(memori_err)
    }

    fn type_distribution(&self, py: Python<'_>) -> PyResult<PyObject> {
        let dist = self
            .inner
            .lock()
            .unwrap()
            .type_distribution()
            .map_err(memori_err)?;
        let dict = PyDict::new_bound(py);
        for (k, v) in dist {
            dict.set_item(k, v)?;
        }
        Ok(dict.to_object(py))
    }

    fn delete_before(&self, before_timestamp: f64) -> PyResult<usize> {
        self.inner
            .lock()
            .unwrap()
            .delete_before(before_timestamp)
            .map_err(memori_err)
    }

    fn delete_by_type(&self, type_value: &str) -> PyResult<usize> {
        self.inner
            .lock()
            .unwrap()
            .delete_by_type(type_value)
            .map_err(memori_err)
    }
}

#[pymodule]
fn memori(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyMemori>()?;
    Ok(())
}
