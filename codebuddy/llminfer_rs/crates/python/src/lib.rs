
use pyo3::{prelude::*, wrap_pymodule};

use diff::StreamNextChunk;


#[pymodule(submodule)]
fn _diff(_py: Python, m: &Bound<PyModule>) -> PyResult<()> {
    m.add_class::<StreamNextChunk>()?;
    Ok(())
}

/// Python module definition
// this name must be same as package name
#[pymodule]
fn llminfer_rs(py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
   // Create the submodule
   let diff_mod = PyModule::new_bound(py, "diff")?;
   _diff(py, &diff_mod)?;
   // Add submodule to the main module
   m.add_submodule(&diff_mod)?;

    Ok(())
}
