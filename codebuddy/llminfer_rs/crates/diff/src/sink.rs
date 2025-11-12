
use imara_diff::sink::Sink;
use std::ops::Range;

#[derive(Debug, Default)]
pub struct ChangeRangeCollector {
    changes: Vec<(Range<u32>, Range<u32>)>,
}

impl Sink for ChangeRangeCollector {
    type Out = Vec<(Range<u32>, Range<u32>)>;

    fn process_change(&mut self, before: Range<u32>, after: Range<u32>) {
        self.changes.push((before, after));
    }

    fn finish(self) -> Self::Out {
        self.changes
    }
}



#[derive(Debug, Default)]
pub struct MatchCollector {
    matches: Vec<(Range<u32>, Range<u32>)>, // (range_in_a, range_in_b)
    last_a: u32,
    last_b: u32,
    total_a_len: u32, // Need total lengths to calculate the final match
    total_b_len: u32,
}

impl MatchCollector {
    pub fn new(total_a_len: u32, total_b_len: u32) -> Self {
        Self {
            total_a_len,
            total_b_len,
            ..Default::default()
        }
    }
}

impl Sink for MatchCollector {
    type Out = Vec<(Range<u32>, Range<u32>)>; // (range_in_a, range_in_b)

    fn process_change(&mut self, before: Range<u32>, after: Range<u32>) {
        // The matching block is the region *before* this change
        // It starts from the end of the last processed position (or 0)
        // and ends at the start of the current change.
        let match_range_a = self.last_a..before.start;
        let match_range_b = self.last_b..after.start;

        // Only add if it's a non-empty match
        if !match_range_a.is_empty() || !match_range_b.is_empty() {
             // Sanity check: lengths should match for an equal block
            assert_eq!(match_range_a.len(), match_range_b.len(), "Match lengths differ unexpectedly");
            self.matches.push((match_range_a, match_range_b));
        }

        // Update the last processed position to the end of this change
        self.last_a = before.end;
        self.last_b = after.end;
    }

    fn finish(mut self) -> Self::Out {
        // Add the final matching block, if any, after the last change
        let final_match_range_a = self.last_a..self.total_a_len;
        let final_match_range_b = self.last_b..self.total_b_len;

        if !final_match_range_a.is_empty() || !final_match_range_b.is_empty() {
            assert_eq!(final_match_range_a.len(), final_match_range_b.len(), "Final match lengths differ unexpectedly");
            self.matches.push((final_match_range_a, final_match_range_b));
        }

        self.matches
    }
}
