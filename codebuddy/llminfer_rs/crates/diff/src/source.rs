
use std::{
    slice::Iter, // Need Iter for the Tokenizer type
    iter::Copied, // Helper to turn Iter<&T> into Iter<T> for Copy types
};

use imara_diff::intern::TokenSource;

#[derive(Debug, Clone, Copy)] // Add derives for convenience
pub struct I32Slice<'a>(pub &'a [i32]);

impl<'a> TokenSource for I32Slice<'a>{
    type Token = i32;
    type Tokenizer = Copied<Iter<'a, i32>>;

    fn tokenize(&self) -> Self::Tokenizer {
        self.0.iter().copied()
    }

    fn estimate_tokens(&self) -> u32 {
        self.0.len() as u32
    }
}
