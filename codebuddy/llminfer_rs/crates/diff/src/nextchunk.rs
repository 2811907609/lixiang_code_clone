
use std::cmp::{min, max};
use std::time::Instant;

use pyo3::Bound;
use pyo3::prelude::*;
use pyo3::types::PyList;

use imara_diff::{
    diff,
    intern::{InternedInput, TokenSource}, // Import TokenSource trait
    Algorithm,
};

use super::source::I32Slice;
use super::sink::MatchCollector;



#[pyclass(module = "stream_chunk_py")]
pub struct StreamNextChunk {
    a: Vec<i32>,
    window_size: usize, // Store calculated window size
    min_window_threshold: usize, // Minimum window size to activate windowing
    a_window_factor: usize, // How much larger the 'a' window should be (e.g., 3x)
}

impl StreamNextChunk {
    /// Creates a new StreamNextChunk instance.
    ///
    /// # Arguments
    ///
    /// * `a` - The reference sequence (like the original file content).
    pub fn new(a_slice: &[i32]) -> Self {
        // Calculate window size based on 'a' length (similar to python)
        // Avoid division by zero for empty 'a'
        let a = a_slice.to_vec();
        let window_size = if a.is_empty() { 0 } else { max(1, a.len() / 15) };
        // Use reasonable defaults or make them configurable
        let min_window_threshold = 100;
        let a_window_factor = 3;

        StreamNextChunk {
            a,
            window_size,
            min_window_threshold,
            a_window_factor,
        }
    }


    /// Predicts the next chunk of `a` based on the matches found in `current_b`.
    /// Applies windowing if `current_b` is sufficiently long.
    ///
    /// # Arguments
    ///
    /// * `current_b` - The sequence received so far.
    /// * `chunk_size` - The desired maximum size of the returned chunk.
    ///
    /// # Returns
    ///
    /// A slice referencing the predicted next chunk within the original `a`.
    pub fn next_chunk(&self, current_b: &[i32], chunk_size: usize) -> &[i32] {
        let result = self._next_chunk(current_b, chunk_size);
        result
    }

    fn _next_chunk(&self, current_b: &[i32], chunk_size: usize) -> &[i32] {
        if self.a.is_empty() || chunk_size == 0 {
            return &[];
        }

        // --- Determine if windowing should be applied ---
        let apply_windowing = !current_b.is_empty()
            && self.window_size > 0 // Avoid windowing if window size is zero
            && self.window_size >= self.min_window_threshold // Only window if size is significant
            && current_b.len() >= self.window_size;

        let a_slice: &[i32]; // The slice of 'a' to diff against
        let b_slice: &[i32]; // The slice of 'b' to use for diffing
        let a_slice_start_offset: usize; // Start index of a_slice within self.a

        if apply_windowing {
            // Calculate slices for windowed diff
            let trim_len = current_b.len() - self.window_size;
            b_slice = &current_b[trim_len..];

            // Calculate 'a' window bounds (similar to python logic)
            // Start 'a' window potentially before the corresponding 'b' start point
            let a_lower_bound = trim_len.saturating_sub(self.window_size);
            // Make 'a' window larger to provide context
            let a_upper_bound = min(self.a.len(), a_lower_bound + self.window_size * self.a_window_factor);
            // Ensure lower bound isn't past upper bound (can happen with short 'a')
            let a_lower_bound_final = min(a_lower_bound, a_upper_bound);

            a_slice = &self.a[a_lower_bound_final..a_upper_bound];
            a_slice_start_offset = a_lower_bound_final; // Remember the offset

            // println!( // Debugging window info
            //     "Windowing: b_len={}, trim_len={}, b_slice_len={}, a_offset={}, a_slice_len={}",
            //     current_b.len(), trim_len, b_slice.len(), a_slice_start_offset, a_slice.len()
            // );

        } else {
            // Use full slices if not windowing
            a_slice = self.a.as_slice();
            b_slice = current_b;
            a_slice_start_offset = 0;
        }

        // --- Perform diff on the selected slices (either full or windowed) ---
        let source_a = I32Slice(a_slice);
        let source_b = I32Slice(b_slice);

        let a_len = source_a.estimate_tokens(); // Length of the slice being diffed
        let b_len = source_b.estimate_tokens(); // Length of the slice being diffed

        // Handle case where b_slice might be empty after trimming but current_b wasn't
        if b_len == 0 && !current_b.is_empty() {
             // If b_slice is empty (e.g., windowing trimmed everything),
             // we can't find matches based on it. Predict from the start of 'a'.
             // This might need refinement depending on desired behavior.
             // A safer bet might be to return empty, assuming the state is unusual.
             // Let's stick to the original "no match" behavior for now:
             let end = min(chunk_size, self.a.len());
             return &self.a[0..end];
        } else if b_len == 0 && current_b.is_empty() {
             // Standard case: b is truly empty, predict start of a
             let end = min(chunk_size, self.a.len());
             return &self.a[0..end];
        }


        let input = InternedInput::<i32>::new(source_a, source_b);
        // Pass the lengths of the *slices* being diffed to the collector
        let sink = MatchCollector::new(a_len, b_len);
        let matches = diff(Algorithm::Histogram, &input, sink);

        // --- Process matches ---
        if matches.is_empty() {
            // No matches found *within the diffed slices*.
            if apply_windowing {
                // If windowing was active and found no match, it's hard to predict.
                // Maybe the match lies outside the window. Returning empty is safest.
                // Alternatively, could try predicting from a_slice_start_offset + window_size?
                // Let's return empty for now.
                 return &[];
            } else {
                // Not windowing, and no matches found at all. Predict start of 'a'.
                let end = min(chunk_size, self.a.len());
                return &self.a[0..end];
            }
        }

        // Get the last match found within the diffed slices
        if let Some(last_match) = matches.last() {
            let (last_match_a_range, last_match_b_range) = last_match;

            // Check if the end of the last match in b_slice aligns with the end of b_slice
            let current_matched = last_match_b_range.end == b_len;

            if !current_matched {
                // b_slice (or current_b if not windowing) ends mid-change or after the last match.
                // Cannot confidently predict.
                return &[];
            }

            // Calculate the offset *within the a_slice* immediately after the last match
            let unmatched_offset_in_a_slice = last_match_a_range.end as usize;

            // --- Crucial: Convert offset back to the original self.a coordinate system ---
            let unmatched_offset_in_original_a = a_slice_start_offset + unmatched_offset_in_a_slice;

            // Check if we've already matched past the end of the original 'a'
            if unmatched_offset_in_original_a >= self.a.len() {
                return &[]; // Nothing more to predict
            }

            // Calculate the end index for the next chunk slice in the original 'a'
            let end_offset_in_original_a = min(unmatched_offset_in_original_a + chunk_size, self.a.len());

            // Return the slice from the *original* self.a
            return &self.a[unmatched_offset_in_original_a..end_offset_in_original_a];

        } else {
            // Should be covered by matches.is_empty(), but handle defensively.
            return &[];
        }
    }
}





#[pymethods]
impl StreamNextChunk {
    /// Creates a new StreamNextChunk instance from a Python list.
    ///
    /// Args:
    ///     a (list[int]): The reference sequence (like the original file content).
    #[new] // This defines the Python constructor (__init__)
    #[pyo3(text_signature = "(a)")]
    fn py_new(a_py: Bound<'_, PyList>) -> PyResult<Self> {
        let a: Vec<i32> = a_py.extract()?;

                // 2. Perform calculations directly here
                let window_size = if a.is_empty() { 0 } else { max(1, a.len() / 15) };
                let min_window_threshold = 100; // Example value
                let a_window_factor = 3;      // Example value

                // 3. Construct the struct directly using the owned 'a' and return it
                Ok(StreamNextChunk {
                    a, // Use the owned Vec directly
                    window_size,
                    min_window_threshold,
                    a_window_factor,
                })
    }

    #[pyo3(name="next_chunk", text_signature = "(current_b, chunk_size)")]
    pub fn next_chunk_py(&self, current_b_py: Bound<'_, PyList>, chunk_size: usize) -> PyResult<Vec<i32>> {
        let current_b: Vec<i32> = current_b_py.extract()?;
        let result = self.next_chunk(current_b.as_slice(), chunk_size);
        Ok(result.to_vec())
    }
}



#[cfg(test)]
mod test {
    use super::*;

    #[test]
    fn test_stream_next_chunk() {
        let original_a = vec![10, 20, 30, 40, 50, 60, 70, 80, 90, 100];
        let mut current_b = Vec::new();
        let chunk_size = 3;

        let streamer = StreamNextChunk::new(&original_a);

        // 1. Initially, b is empty. Predict the first chunk of a.
        let next = streamer.next_chunk(&current_b, chunk_size);
        assert_eq!(next, &[10, 20, 30]);
        println!("B: {:?}, Next A chunk: {:?}", current_b, next);
        current_b.extend_from_slice(next); // Simulate receiving/appending the chunk

        // 2. b now matches the start of a. Predict the next chunk.
        let next = streamer.next_chunk(&current_b, chunk_size);
        assert_eq!(next, &[40, 50, 60]);
        println!("B: {:?}, Next A chunk: {:?}", current_b, next);
        current_b.extend_from_slice(next);

        // 3. Continue predicting
        let next = streamer.next_chunk(&current_b, chunk_size);
        assert_eq!(next, &[70, 80, 90]);
        println!("B: {:?}, Next A chunk: {:?}", current_b, next);
        current_b.extend_from_slice(next);

        // 4. Predict the final chunk (might be smaller than chunk_size)
        let next = streamer.next_chunk(&current_b, chunk_size);
        assert_eq!(next, &[100]);
        println!("B: {:?}, Next A chunk: {:?}", current_b, next);
        current_b.extend_from_slice(next);

        // 5. b now matches a completely. Prediction should be empty.
        let next = streamer.next_chunk(&current_b, chunk_size);
        assert_eq!(next, &[] as &[i32]);
        println!("B: {:?}, Next A chunk: {:?}", current_b, next);

        // --- Test case with a mismatch ---
        let original_a2 = vec![1, 2, 3, 4, 5, 6];
        let streamer2 = StreamNextChunk::new(&original_a2);
        let current_b2 = vec![1, 2, 99]; // Introduce a mismatch

        // b ends with data (99) that doesn't align with the end of the last match (1, 2).
        // Prediction should be empty.
        let next = streamer2.next_chunk(&current_b2, chunk_size);
        assert_eq!(next, &[] as &[i32]);
        println!("B2: {:?}, Next A chunk: {:?}", current_b2, next);

        // --- Test case starting empty ---
        let original_a3 = vec![1, 2, 3];
        let streamer3 = StreamNextChunk::new(&original_a3);
        let current_b3 = vec![];
        let next = streamer3.next_chunk(&current_b3, 2);
        assert_eq!(next, &[1, 2]);
        println!("B3: {:?}, Next A chunk: {:?}", current_b3, next);

        // --- Test case empty 'a' ---
        let original_a4 : Vec<i32> = vec![];
        let streamer4 = StreamNextChunk::new(&original_a4);
        let current_b4 = vec![1, 2];
        let next = streamer4.next_chunk(&current_b4, 2);
        assert_eq!(next, &[] as &[i32]);
        println!("B4: {:?}, Next A chunk: {:?}", current_b4, next);

        // --- Test case empty 'b' but 'a' has content ---
        let original_a5 = vec![10, 20];
        let streamer5 = StreamNextChunk::new(&original_a5);
        let current_b5 : Vec<i32> = vec![];
        let next = streamer5.next_chunk(&current_b5, 3);
        assert_eq!(next, &[10, 20]);
        println!("B5: {:?}, Next A chunk: {:?}", current_b5, next);
    }



    #[test]
    fn test_real_case1_simulation() {
        // --- Placeholder Data ---
        // Replace these with your actual _long_testcase data
        // let input_tokens: Vec<i32> = _long_testcase[0].to_vec(); // Example if loaded elsewhere
        // let output_tokens: Vec<i32> = _long_testcase[1].to_vec();
        let input_tokens: Vec<i32> = (1..=1000).collect(); // Mock data 1
        let mut output_tokens: Vec<i32> = (1..=500).collect(); // Mock data 2 (shorter)
        // Simulate some differences for a more realistic test
        output_tokens[10] = 999;
        output_tokens[100] = 888;
        output_tokens.extend(501..=1000); // Add the rest matching input
        output_tokens[600] = 777; // Another difference
        // --- End Placeholder Data ---

        let mut current_idx: usize = 0;
        let spec_num_tokens: usize = 80; // chunk_size for prediction
        let mut iter: u32 = 0;
        let mut total_accepted: usize = 0;
        let mut first_token_duration: Option<Duration> = None; // Use Option for clarity

        // Create the streamer instance
        let streamer = StreamNextChunk::new(&input_tokens);

        println!("Input token count: {}", input_tokens.len());
        println!("Output token count: {}", output_tokens.len());
        println!("Chunk size: {}", spec_num_tokens);

        let start_time = Instant::now(); // Start timing

        while current_idx < output_tokens.len() {
            iter += 1;
            // println!("Iteration {}: Current output index: {}", iter, current_idx); // Optional detailed log

            // Get the portion of output_tokens processed so far
            let current_b_slice = &output_tokens[0..current_idx];

            // Predict the next chunk based on current_b
            let predict_chunk = streamer.next_chunk(current_b_slice, spec_num_tokens);

            // Record time for the first prediction
            if first_token_duration.is_none() {
                first_token_duration = Some(start_time.elapsed());
            }

            if predict_chunk.is_empty() && current_idx < output_tokens.len() {
                // If prediction is empty but we aren't finished, it means there was likely
                // a mismatch preventing prediction. We must advance by at least 1
                // to potentially find a new match point later.
                println!("Iteration {}: Prediction empty, advancing by 1.", iter);
                current_idx += 1;
                continue; // Skip comparison for this iteration
            } else if predict_chunk.is_empty() {
                // Prediction is empty and we are likely at the end or cannot predict further
                println!("Iteration {}: Prediction empty, loop should terminate.", iter);
                break; // Exit loop
            }


            // Determine the actual next chunk from the target output
            let actual_chunk_end = min(current_idx + predict_chunk.len(), output_tokens.len());
            let actual_chunk = &output_tokens[current_idx..actual_chunk_end];

            // Compare predicted chunk with actual chunk to find accepted tokens
            let accepted = predict_chunk
                .iter()
                .zip(actual_chunk.iter()) // Pair up tokens
                .take_while(|(predicted, actual)| predicted == actual) // Count matching prefix
                .count();

            println!(
                "Iteration {}: Predicted len {}, Accepted: {}",
                iter,
                predict_chunk.len(),
                accepted
            );

            // Advance current_idx by the number of accepted tokens, or at least 1
            let advance_by = max(accepted, 1);
            current_idx += advance_by;

            // Accumulate total accepted tokens (only add the truly matched ones)
            total_accepted += accepted;

            // Optional: Log progress
            // println!("  Advanced by {}, New index: {}", advance_by, current_idx);
        }

        let total_duration = start_time.elapsed();

        println!("\n--- Simulation Summary ---");
        println!("Total Iterations: {}", iter);
        println!("Total Accepted Tokens: {} (out of {})", total_accepted, output_tokens.len());
        if let Some(ftd) = first_token_duration {
            println!("First Prediction Time: {:.3} ms", ftd.as_secs_f64() * 1000.0);
        } else {
            println!("First Prediction Time: N/A (no predictions made)");
        }
        println!("Total Simulation Time: {:.3} ms", total_duration.as_secs_f64() * 1000.0);

        // Optional: Add assertions for testing purposes if you have expected outcomes
        // assert!(total_accepted > 0, "Should have accepted some tokens");
        // assert_eq!(current_idx, output_tokens.len(), "Should have processed all output tokens");
    }
}
