import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from data_scrap.tools.gerrit import scrap_changes


class TestFallbackSyncCandidates:
    """Test cases for the get_fallback_sync_candidates function"""

    def test_get_common_where_conditions(self):
        """Test that common WHERE conditions are properly formatted"""
        conditions = scrap_changes.get_common_where_conditions()

        # Verify key conditions are present
        assert 'scrap_task_status is distinct from \'doing\'' in conditions
        assert 'last_failed_time is null or last_failed_time < now() - interval \'60 seconds\'' in conditions
        assert 'event_type is null or event_type not in (\'change-deleted\')' in conditions
        assert 'private is distinct from true' in conditions
        assert 'continuous_failed_count is null or continuous_failed_count <= 10' in conditions
        assert 'failed_reason is null' in conditions

    @patch.object(scrap_changes, 'execute_sql')
    def test_get_fallback_sync_candidates_basic(self, mock_execute_sql):
        """Test basic functionality of get_fallback_sync_candidates"""
        # Mock return data
        mock_data = [
            {
                'change_id': 12345,
                'repo': 'test/repo1',
                'change_status': 'NEW',
                'last_scrap_at': datetime.now() - timedelta(hours=10),
                'last_event_at': datetime.now() - timedelta(hours=20),
                'last_fallback_processed_at': None
            },
            {
                'change_id': 12346,
                'repo': 'test/repo2',
                'change_status': 'NEW',
                'last_scrap_at': datetime.now() - timedelta(hours=50),
                'last_event_at': datetime.now() - timedelta(hours=100),
                'last_fallback_processed_at': datetime.now() - timedelta(hours=25)
            }
        ]
        mock_execute_sql.return_value = mock_data

        result = scrap_changes.get_fallback_sync_candidates()

        # Verify execute_sql was called once
        mock_execute_sql.assert_called_once()

        # Verify the SQL query structure
        sql_call = mock_execute_sql.call_args[0][0]
        assert 'interval \'8 hours\'' in sql_call
        assert 'interval \'120 hours\'' in sql_call
        assert 'change_status = \'NEW\'' in sql_call
        assert 'interval \'24 hours\'' in sql_call
        assert 'limit 100' in sql_call
        assert 'last_fallback_processed_at asc nulls first' in sql_call
        assert '(last_scrap_at - last_event_at) desc' in sql_call

        # Verify result
        assert result == mock_data
        assert len(result) == 2

    @patch.object(scrap_changes, 'execute_sql')
    def test_get_fallback_sync_candidates_empty_result(self, mock_execute_sql):
        """Test when no candidates are found"""
        mock_execute_sql.return_value = []

        result = scrap_changes.get_fallback_sync_candidates()

        mock_execute_sql.assert_called_once()
        assert result == []

    @patch.object(scrap_changes, 'execute_sql')
    def test_get_fallback_sync_candidates_none_result(self, mock_execute_sql):
        """Test when execute_sql returns None"""
        mock_execute_sql.return_value = None

        result = scrap_changes.get_fallback_sync_candidates()

        mock_execute_sql.assert_called_once()
        assert result is None

    @patch.object(scrap_changes, 'execute_sql')
    def test_get_fallback_sync_candidates_sql_structure(self, mock_execute_sql):
        """Test the SQL query structure in detail"""
        mock_execute_sql.return_value = []

        scrap_changes.get_fallback_sync_candidates()

        sql_call = mock_execute_sql.call_args[0][0]

        # Test time gap conditions
        assert '(last_scrap_at - last_event_at) >= interval \'8 hours\'' in sql_call
        assert '(last_scrap_at - last_event_at) <= interval \'120 hours\'' in sql_call

        # Test status filter
        assert 'change_status = \'NEW\'' in sql_call

        # Test recent activity filter (7-day window)
        assert 'last_event_at >= now() - interval \'7 days\'' in sql_call

        # Test cooldown logic
        assert '(last_fallback_processed_at is null or last_fallback_processed_at < now() - interval \'24 hours\')' in sql_call

        # Test ordering
        assert 'order by' in sql_call.lower()
        assert 'last_fallback_processed_at asc nulls first' in sql_call
        assert '(last_scrap_at - last_event_at) desc' in sql_call

        # Test limit
        assert 'limit 100' in sql_call

        # Test common conditions are included
        assert 'scrap_task_status is distinct from \'doing\'' in sql_call
        assert 'private is distinct from true' in sql_call

    @patch.object(scrap_changes, 'execute_sql')
    def test_get_fallback_sync_candidates_with_common_conditions(self, mock_execute_sql):
        """Test that common WHERE conditions are properly integrated"""
        mock_execute_sql.return_value = []

        scrap_changes.get_fallback_sync_candidates()

        sql_call = mock_execute_sql.call_args[0][0]

        # Verify all common conditions are present in the fallback query
        expected_common_conditions = [
            'scrap_task_status is distinct from \'doing\'',
            'last_failed_time is null or last_failed_time < now() - interval \'60 seconds\'',
            'event_type is null or event_type not in (\'change-deleted\')',
            'private is distinct from true',
            'continuous_failed_count is null or continuous_failed_count <= 10',
            'failed_reason is null'
        ]

        for condition in expected_common_conditions:
            assert condition in sql_call

    @patch.object(scrap_changes, 'execute_sql')
    def test_get_fallback_sync_candidates_large_dataset(self, mock_execute_sql):
        """Test with a large dataset to verify limit is applied"""
        # Create mock data with 150 items (more than the 100 limit)
        mock_data = []
        for i in range(150):
            mock_data.append({
                'change_id': 10000 + i,
                'repo': f'test/repo{i}',
                'change_status': 'NEW',
                'last_scrap_at': datetime.now() - timedelta(hours=10),
                'last_event_at': datetime.now() - timedelta(hours=20),
                'last_fallback_processed_at': None
            })

        # But execute_sql should only return 100 due to LIMIT clause
        mock_execute_sql.return_value = mock_data[:100]

        result = scrap_changes.get_fallback_sync_candidates()

        mock_execute_sql.assert_called_once()
        sql_call = mock_execute_sql.call_args[0][0]
        assert 'limit 100' in sql_call
        assert len(result) == 100

    @patch.object(scrap_changes, 'execute_sql')
    def test_get_fallback_sync_candidates_sql_injection_safety(self, mock_execute_sql):
        """Test that the SQL query is safe from injection (no user input)"""
        mock_execute_sql.return_value = []

        scrap_changes.get_fallback_sync_candidates()

        sql_call = mock_execute_sql.call_args[0][0]

        # Verify no user input is directly interpolated
        # All values should be hardcoded strings or intervals
        assert 'interval \'8 hours\'' in sql_call
        assert 'interval \'120 hours\'' in sql_call
        assert 'interval \'24 hours\'' in sql_call
        assert '\'NEW\'' in sql_call
        assert 'limit 100' in sql_call

        # Verify execute_sql is called with just the SQL string (no parameters)
        assert len(mock_execute_sql.call_args[0]) == 1  # Only SQL string, no parameters

    @patch.object(scrap_changes, 'execute_sql')
    def test_get_fallback_sync_candidates_ordering_priority(self, mock_execute_sql):
        """Test that the ordering prioritizes unprocessed changes correctly"""
        mock_execute_sql.return_value = []

        scrap_changes.get_fallback_sync_candidates()

        sql_call = mock_execute_sql.call_args[0][0]

        # Find the ORDER BY clause
        order_by_index = sql_call.lower().find('order by')
        assert order_by_index != -1

        order_clause = sql_call[order_by_index:]

        # Verify the ordering: nulls first (unprocessed), then by time gap desc
        assert 'last_fallback_processed_at asc nulls first' in order_clause
        assert '(last_scrap_at - last_event_at) desc' in order_clause

        # Verify nulls first comes before time gap ordering
        nulls_first_index = order_clause.find('nulls first')
        time_gap_index = order_clause.find('(last_scrap_at - last_event_at) desc')
        assert nulls_first_index < time_gap_index


class TestUpdateFallbackProcessedTimestamp:
    """Test cases for the update_fallback_processed_timestamp function"""

    @patch.object(scrap_changes, 'execute_sql')
    def test_update_fallback_processed_timestamp_success(self, mock_execute_sql):
        """Test successful timestamp update"""
        mock_execute_sql.return_value = None  # UPDATE queries don't return data

        result = scrap_changes.update_fallback_processed_timestamp(12345, 'test/repo')

        # Verify execute_sql was called with correct parameters
        mock_execute_sql.assert_called_once_with(
            '''
UPDATE gerrit_change_task_queue
SET last_fallback_processed_at = now()
WHERE change_id = %s AND repo = %s
''',
            (12345, 'test/repo'),
            commit=True
        )

        # Verify function returns True on success
        assert result is True

    @patch.object(scrap_changes, 'execute_sql')
    def test_update_fallback_processed_timestamp_failure(self, mock_execute_sql):
        """Test timestamp update failure handling"""
        # Mock execute_sql to raise an exception
        mock_execute_sql.side_effect = Exception("Database connection failed")

        result = scrap_changes.update_fallback_processed_timestamp(12345, 'test/repo')

        # Verify execute_sql was called
        mock_execute_sql.assert_called_once_with(
            '''
UPDATE gerrit_change_task_queue
SET last_fallback_processed_at = now()
WHERE change_id = %s AND repo = %s
''',
            (12345, 'test/repo'),
            commit=True
        )

        # Verify function returns False on failure
        assert result is False

    @patch.object(scrap_changes, 'execute_sql')
    def test_update_fallback_processed_timestamp_sql_structure(self, mock_execute_sql):
        """Test the SQL query structure and parameters"""
        mock_execute_sql.return_value = None

        change_id = 98765
        repo = 'project/repository-name'

        scrap_changes.update_fallback_processed_timestamp(change_id, repo)

        # Verify the call structure
        call_args = mock_execute_sql.call_args
        sql_query = call_args[0][0]
        parameters = call_args[0][1]
        commit_flag = call_args[1]['commit']

        # Verify SQL query structure
        assert 'UPDATE gerrit_change_task_queue' in sql_query
        assert 'SET last_fallback_processed_at = now()' in sql_query
        assert 'WHERE change_id = %s AND repo = %s' in sql_query

        # Verify parameters
        assert parameters == (change_id, repo)

        # Verify commit flag
        assert commit_flag is True

    @patch.object(scrap_changes, 'execute_sql')
    def test_update_fallback_processed_timestamp_different_data_types(self, mock_execute_sql):
        """Test with different data types for change_id and repo"""
        mock_execute_sql.return_value = None

        # Test with string change_id (should work)
        result1 = scrap_changes.update_fallback_processed_timestamp('12345', 'test/repo')
        assert result1 is True

        # Test with integer change_id (should work)
        result2 = scrap_changes.update_fallback_processed_timestamp(12345, 'test/repo')
        assert result2 is True

        # Test with repo containing special characters
        result3 = scrap_changes.update_fallback_processed_timestamp(12345, 'test/repo-with-dashes_and_underscores')
        assert result3 is True

        # Verify all calls were made
        assert mock_execute_sql.call_count == 3

    @patch.object(scrap_changes, 'execute_sql')
    @patch.object(scrap_changes.logging, 'info')
    @patch.object(scrap_changes.logging, 'error')
    def test_update_fallback_processed_timestamp_logging(self, mock_log_error, mock_log_info, mock_execute_sql):
        """Test logging behavior for both success and failure cases"""
        # Test success logging
        mock_execute_sql.return_value = None

        result = scrap_changes.update_fallback_processed_timestamp(12345, 'test/repo')

        assert result is True
        mock_log_info.assert_called_once_with('Updated fallback processed timestamp for change 12345 in repo test/repo')
        mock_log_error.assert_not_called()

        # Reset mocks
        mock_log_info.reset_mock()
        mock_log_error.reset_mock()

        # Test failure logging
        mock_execute_sql.side_effect = Exception("Database error")

        result = scrap_changes.update_fallback_processed_timestamp(67890, 'another/repo')

        assert result is False
        mock_log_info.assert_not_called()
        mock_log_error.assert_called_once_with('Failed to update fallback processed timestamp for change 67890 in repo another/repo: Database error')

    @patch.object(scrap_changes, 'execute_sql')
    def test_update_fallback_processed_timestamp_sql_injection_safety(self, mock_execute_sql):
        """Test that the function is safe from SQL injection"""
        mock_execute_sql.return_value = None

        # Test with potentially malicious input
        malicious_change_id = "12345; DROP TABLE gerrit_change_task_queue; --"
        malicious_repo = "test'; DELETE FROM gerrit_change_task_queue WHERE '1'='1"

        scrap_changes.update_fallback_processed_timestamp(malicious_change_id, malicious_repo)

        # Verify that parameters are passed safely (not interpolated into SQL)
        call_args = mock_execute_sql.call_args
        sql_query = call_args[0][0]
        parameters = call_args[0][1]

        # SQL should contain placeholders, not actual values
        assert '%s' in sql_query
        assert 'DROP TABLE' not in sql_query
        assert 'DELETE FROM' not in sql_query

        # Parameters should contain the original values
        assert parameters == (malicious_change_id, malicious_repo)

    @patch.object(scrap_changes, 'execute_sql')
    def test_update_fallback_processed_timestamp_edge_cases(self, mock_execute_sql):
        """Test edge cases for change_id and repo parameters"""
        mock_execute_sql.return_value = None

        # Test with zero change_id
        result1 = scrap_changes.update_fallback_processed_timestamp(0, 'test/repo')
        assert result1 is True

        # Test with negative change_id
        result2 = scrap_changes.update_fallback_processed_timestamp(-1, 'test/repo')
        assert result2 is True

        # Test with empty repo string
        result3 = scrap_changes.update_fallback_processed_timestamp(12345, '')
        assert result3 is True

        # Test with very long repo name
        long_repo = 'a' * 1000
        result4 = scrap_changes.update_fallback_processed_timestamp(12345, long_repo)
        assert result4 is True

        # Verify all calls were made
        assert mock_execute_sql.call_count == 4

    @patch.object(scrap_changes, 'execute_sql')
    def test_update_fallback_processed_timestamp_commit_behavior(self, mock_execute_sql):
        """Test that the function always commits the transaction"""
        mock_execute_sql.return_value = None

        scrap_changes.update_fallback_processed_timestamp(12345, 'test/repo')

        # Verify commit=True is always passed
        call_args = mock_execute_sql.call_args
        assert call_args[1]['commit'] is True

    @patch.object(scrap_changes, 'execute_sql')
    def test_update_fallback_processed_timestamp_return_values(self, mock_execute_sql):
        """Test return values in various scenarios"""
        # Test successful execution
        mock_execute_sql.return_value = None
        result = scrap_changes.update_fallback_processed_timestamp(12345, 'test/repo')
        assert result is True
        assert isinstance(result, bool)

        # Test exception handling
        mock_execute_sql.side_effect = Exception("Test error")
        result = scrap_changes.update_fallback_processed_timestamp(12345, 'test/repo')
        assert result is False
        assert isinstance(result, bool)


class TestProcessFallbackChanges:
    """Test cases for the process_fallback_changes function"""

    @pytest.mark.asyncio
    @patch.object(scrap_changes, 'update_fallback_processed_timestamp')
    @patch.object(scrap_changes, 'refresh_item')
    async def test_process_fallback_changes_empty_list(self, mock_refresh_item, mock_update_timestamp):
        """Test processing with empty candidate list"""
        result = await scrap_changes.process_fallback_changes([])

        # Verify no functions were called
        mock_update_timestamp.assert_not_called()
        mock_refresh_item.assert_not_called()

        # Verify return structure
        expected = {
            'success_count': 0,
            'error_count': 0,
            'errors': []
        }
        assert result == expected

    @pytest.mark.asyncio
    @patch.object(scrap_changes, 'update_fallback_processed_timestamp')
    @patch.object(scrap_changes, 'refresh_item')
    async def test_process_fallback_changes_none_input(self, mock_refresh_item, mock_update_timestamp):
        """Test processing with None input"""
        result = await scrap_changes.process_fallback_changes(None)

        # Verify no functions were called
        mock_update_timestamp.assert_not_called()
        mock_refresh_item.assert_not_called()

        # Verify return structure
        expected = {
            'success_count': 0,
            'error_count': 0,
            'errors': []
        }
        assert result == expected

    @pytest.mark.asyncio
    @patch('asyncio.sleep')
    @patch.object(scrap_changes, 'update_fallback_processed_timestamp')
    @patch.object(scrap_changes, 'refresh_item')
    async def test_process_fallback_changes_single_success(self, mock_refresh_item, mock_update_timestamp, mock_sleep):
        """Test successful processing of a single change"""
        # Setup mocks
        mock_update_timestamp.return_value = True
        mock_refresh_item.return_value = None  # refresh_item doesn't return anything on success
        mock_sleep.return_value = None  # Mock sleep to avoid delays

        # Test data
        candidate_changes = [
            {
                'change_id': 12345,
                'repo': 'test/repo1',
                'change_status': 'NEW'
            }
        ]

        result = await scrap_changes.process_fallback_changes(candidate_changes)

        # Verify function calls
        mock_update_timestamp.assert_called_once_with(12345, 'test/repo1')
        mock_refresh_item.assert_called_once_with(candidate_changes[0])
        mock_sleep.assert_called_once_with(2)  # Verify sleep was called with 2 seconds

        # Verify result
        expected = {
            'success_count': 1,
            'error_count': 0,
            'errors': []
        }
        assert result == expected

    @pytest.mark.asyncio
    @patch('asyncio.sleep')
    @patch.object(scrap_changes, 'update_fallback_processed_timestamp')
    @patch.object(scrap_changes, 'refresh_item')
    async def test_process_fallback_changes_multiple_success(self, mock_refresh_item, mock_update_timestamp, mock_sleep):
        """Test successful processing of multiple changes"""
        # Setup mocks
        mock_update_timestamp.return_value = True
        mock_refresh_item.return_value = None
        mock_sleep.return_value = None  # Mock sleep to avoid delays

        # Test data
        candidate_changes = [
            {'change_id': 12345, 'repo': 'test/repo1', 'change_status': 'NEW'},
            {'change_id': 12346, 'repo': 'test/repo2', 'change_status': 'NEW'},
            {'change_id': 12347, 'repo': 'test/repo3', 'change_status': 'NEW'}
        ]

        result = await scrap_changes.process_fallback_changes(candidate_changes)

        # Verify function calls
        assert mock_update_timestamp.call_count == 3
        assert mock_refresh_item.call_count == 3
        assert mock_sleep.call_count == 3  # Sleep called after each successful processing

        # Verify specific calls
        mock_update_timestamp.assert_any_call(12345, 'test/repo1')
        mock_update_timestamp.assert_any_call(12346, 'test/repo2')
        mock_update_timestamp.assert_any_call(12347, 'test/repo3')

        mock_refresh_item.assert_any_call(candidate_changes[0])
        mock_refresh_item.assert_any_call(candidate_changes[1])
        mock_refresh_item.assert_any_call(candidate_changes[2])

        mock_sleep.assert_called_with(2)  # Verify sleep duration

        # Verify result
        expected = {
            'success_count': 3,
            'error_count': 0,
            'errors': []
        }
        assert result == expected

    @pytest.mark.asyncio
    @patch.object(scrap_changes, 'update_fallback_processed_timestamp')
    @patch.object(scrap_changes, 'refresh_item')
    async def test_process_fallback_changes_timestamp_update_failure(self, mock_refresh_item, mock_update_timestamp):
        """Test handling of timestamp update failure"""
        # Setup mocks - timestamp update fails
        mock_update_timestamp.return_value = False
        mock_refresh_item.return_value = None

        # Test data
        candidate_changes = [
            {'change_id': 12345, 'repo': 'test/repo1', 'change_status': 'NEW'}
        ]

        result = await scrap_changes.process_fallback_changes(candidate_changes)

        # Verify timestamp update was called but refresh_item was not
        mock_update_timestamp.assert_called_once_with(12345, 'test/repo1')
        mock_refresh_item.assert_not_called()

        # Verify result
        expected = {
            'success_count': 0,
            'error_count': 1,
            'errors': [
                {
                    'change_id': 12345,
                    'repo': 'test/repo1',
                    'error': 'Failed to update fallback timestamp for change 12345 in repo test/repo1',
                    'stage': 'timestamp_update'
                }
            ]
        }
        assert result == expected

    @pytest.mark.asyncio
    @patch.object(scrap_changes, 'update_fallback_processed_timestamp')
    @patch.object(scrap_changes, 'refresh_item')
    async def test_process_fallback_changes_refresh_item_failure(self, mock_refresh_item, mock_update_timestamp):
        """Test handling of refresh_item failure"""
        # Setup mocks - refresh_item raises exception
        mock_update_timestamp.return_value = True
        mock_refresh_item.side_effect = Exception("Gerrit connection failed")

        # Test data
        candidate_changes = [
            {'change_id': 12345, 'repo': 'test/repo1', 'change_status': 'NEW'}
        ]

        result = await scrap_changes.process_fallback_changes(candidate_changes)

        # Verify both functions were called
        mock_update_timestamp.assert_called_once_with(12345, 'test/repo1')
        mock_refresh_item.assert_called_once_with(candidate_changes[0])

        # Verify result
        expected = {
            'success_count': 0,
            'error_count': 1,
            'errors': [
                {
                    'change_id': 12345,
                    'repo': 'test/repo1',
                    'error': 'Gerrit connection failed',
                    'stage': 'processing'
                }
            ]
        }
        assert result == expected

    @pytest.mark.asyncio
    @patch('asyncio.sleep')
    @patch.object(scrap_changes, 'update_fallback_processed_timestamp')
    @patch.object(scrap_changes, 'refresh_item')
    async def test_process_fallback_changes_mixed_results(self, mock_refresh_item, mock_update_timestamp, mock_sleep):
        """Test processing with mixed success and failure results"""
        # Setup mocks with different behaviors for different calls
        def timestamp_side_effect(change_id, repo):
            if change_id == 12346:  # Second change fails timestamp update
                return False
            return True

        def refresh_side_effect(change):
            if change['change_id'] == 12347:  # Third change fails processing
                raise Exception("Processing failed")
            return None

        mock_update_timestamp.side_effect = timestamp_side_effect
        mock_refresh_item.side_effect = refresh_side_effect
        mock_sleep.return_value = None  # Mock sleep to avoid delays

        # Test data
        candidate_changes = [
            {'change_id': 12345, 'repo': 'test/repo1', 'change_status': 'NEW'},  # Success
            {'change_id': 12346, 'repo': 'test/repo2', 'change_status': 'NEW'},  # Timestamp failure
            {'change_id': 12347, 'repo': 'test/repo3', 'change_status': 'NEW'}   # Processing failure
        ]

        result = await scrap_changes.process_fallback_changes(candidate_changes)

        # Verify function calls
        assert mock_update_timestamp.call_count == 3
        assert mock_refresh_item.call_count == 2  # Only called for first and third (second failed timestamp)
        assert mock_sleep.call_count == 1  # Only called after successful processing (first change)

        # Verify result
        assert result['success_count'] == 1
        assert result['error_count'] == 2
        assert len(result['errors']) == 2

        # Check specific errors
        error_change_ids = [error['change_id'] for error in result['errors']]
        assert 12346 in error_change_ids  # Timestamp failure
        assert 12347 in error_change_ids  # Processing failure

        # Check error stages
        error_stages = [error['stage'] for error in result['errors']]
        assert 'timestamp_update' in error_stages
        assert 'processing' in error_stages

    @pytest.mark.asyncio
    @patch('asyncio.sleep')
    @patch.object(scrap_changes, 'update_fallback_processed_timestamp')
    @patch.object(scrap_changes, 'refresh_item')
    async def test_process_fallback_changes_continues_after_error(self, mock_refresh_item, mock_update_timestamp, mock_sleep):
        """Test that processing continues after individual change errors"""
        # Setup mocks - first change fails, second succeeds
        def refresh_side_effect(change):
            if change['change_id'] == 12345:
                raise Exception("First change failed")
            return None

        mock_update_timestamp.return_value = True
        mock_refresh_item.side_effect = refresh_side_effect
        mock_sleep.return_value = None  # Mock sleep to avoid delays

        # Test data
        candidate_changes = [
            {'change_id': 12345, 'repo': 'test/repo1', 'change_status': 'NEW'},  # Fails
            {'change_id': 12346, 'repo': 'test/repo2', 'change_status': 'NEW'}   # Succeeds
        ]

        result = await scrap_changes.process_fallback_changes(candidate_changes)

        # Verify both changes were attempted
        assert mock_update_timestamp.call_count == 2
        assert mock_refresh_item.call_count == 2
        assert mock_sleep.call_count == 1  # Only called after successful processing (second change)

        # Verify result shows one success and one failure
        expected = {
            'success_count': 1,
            'error_count': 1,
            'errors': [
                {
                    'change_id': 12345,
                    'repo': 'test/repo1',
                    'error': 'First change failed',
                    'stage': 'processing'
                }
            ]
        }
        assert result == expected

    @pytest.mark.asyncio
    @patch.object(scrap_changes, 'update_fallback_processed_timestamp')
    @patch.object(scrap_changes, 'refresh_item')
    async def test_process_fallback_changes_error_details(self, mock_refresh_item, mock_update_timestamp):
        """Test that error details are properly captured"""
        # Setup mocks
        mock_update_timestamp.return_value = True
        mock_refresh_item.side_effect = ValueError("Invalid change data format")

        # Test data
        candidate_changes = [
            {'change_id': 99999, 'repo': 'special/repo-name', 'change_status': 'NEW'}
        ]

        result = await scrap_changes.process_fallback_changes(candidate_changes)

        # Verify error details
        assert result['error_count'] == 1
        assert len(result['errors']) == 1

        error = result['errors'][0]
        assert error['change_id'] == 99999
        assert error['repo'] == 'special/repo-name'
        assert error['error'] == 'Invalid change data format'
        assert error['stage'] == 'processing'

    @pytest.mark.asyncio
    @patch.object(scrap_changes, 'update_fallback_processed_timestamp')
    @patch.object(scrap_changes, 'refresh_item')
    async def test_process_fallback_changes_preserves_change_data(self, mock_refresh_item, mock_update_timestamp):
        """Test that original change data is passed to refresh_item unchanged"""
        mock_update_timestamp.return_value = True
        mock_refresh_item.return_value = None

        # Test data with additional fields
        candidate_changes = [
            {
                'change_id': 12345,
                'repo': 'test/repo1',
                'change_status': 'NEW',
                'last_scrap_at': datetime.now() - timedelta(hours=10),
                'last_event_at': datetime.now() - timedelta(hours=20),
                'additional_field': 'test_value'
            }
        ]

        await scrap_changes.process_fallback_changes(candidate_changes)

        # Verify refresh_item was called with the exact same change object
        mock_refresh_item.assert_called_once_with(candidate_changes[0])


class TestFallbackSyncLoop:
    """Test cases for the fallback_sync_loop function"""

    @pytest.mark.asyncio
    @patch.object(scrap_changes, 'get_fallback_sync_candidates')
    @patch.object(scrap_changes, 'process_fallback_changes')
    @patch('asyncio.sleep')
    async def test_fallback_sync_loop_no_candidates(self, mock_sleep, mock_process_changes, mock_get_candidates):
        """Test fallback sync loop when no candidates are found"""
        # Setup mocks
        mock_get_candidates.return_value = []
        mock_process_changes.return_value = {
            'success_count': 0,
            'error_count': 0,
            'errors': []
        }

        # Mock sleep to break the infinite loop after first iteration
        mock_sleep.side_effect = [asyncio.CancelledError()]

        # Run the function and expect it to be cancelled after first iteration
        with pytest.raises(asyncio.CancelledError):
            await scrap_changes.fallback_sync_loop()

        # Verify function calls
        mock_get_candidates.assert_called_once()
        mock_process_changes.assert_not_called()  # Should not process when no candidates

        # Verify sleep was called with 12 hours (43200 seconds)
        mock_sleep.assert_called_with(60 * 60 * 12)

    @pytest.mark.asyncio
    @patch.object(scrap_changes, 'get_fallback_sync_candidates')
    @patch.object(scrap_changes, 'process_fallback_changes')
    @patch('asyncio.sleep')
    async def test_fallback_sync_loop_with_candidates(self, mock_sleep, mock_process_changes, mock_get_candidates):
        """Test fallback sync loop with candidate changes"""
        # Setup test data
        candidate_changes = [
            {'change_id': 12345, 'repo': 'test/repo1', 'change_status': 'NEW'},
            {'change_id': 12346, 'repo': 'test/repo2', 'change_status': 'NEW'}
        ]

        # Setup mocks
        mock_get_candidates.return_value = candidate_changes
        mock_process_changes.return_value = {
            'success_count': 2,
            'error_count': 0,
            'errors': []
        }

        # Mock sleep to break the infinite loop after first iteration
        mock_sleep.side_effect = [asyncio.CancelledError()]

        # Run the function and expect it to be cancelled after first iteration
        with pytest.raises(asyncio.CancelledError):
            await scrap_changes.fallback_sync_loop()

        # Verify function calls
        mock_get_candidates.assert_called_once()
        mock_process_changes.assert_called_once_with(candidate_changes)

        # Verify sleep was called with 12 hours
        mock_sleep.assert_called_with(60 * 60 * 12)

    @pytest.mark.asyncio
    @patch.object(scrap_changes, 'get_fallback_sync_candidates')
    @patch.object(scrap_changes, 'process_fallback_changes')
    @patch('asyncio.sleep')
    async def test_fallback_sync_loop_with_processing_errors(self, mock_sleep, mock_process_changes, mock_get_candidates):
        """Test fallback sync loop when processing encounters errors"""
        # Setup test data
        candidate_changes = [
            {'change_id': 12345, 'repo': 'test/repo1', 'change_status': 'NEW'},
            {'change_id': 12346, 'repo': 'test/repo2', 'change_status': 'NEW'}
        ]

        # Setup mocks with processing errors
        mock_get_candidates.return_value = candidate_changes
        mock_process_changes.return_value = {
            'success_count': 1,
            'error_count': 1,
            'errors': [
                {
                    'change_id': 12346,
                    'repo': 'test/repo2',
                    'error': 'Processing failed',
                    'stage': 'processing'
                }
            ]
        }

        # Mock sleep to break the infinite loop after first iteration
        mock_sleep.side_effect = [asyncio.CancelledError()]

        # Run the function and expect it to be cancelled after first iteration
        with pytest.raises(asyncio.CancelledError):
            await scrap_changes.fallback_sync_loop()

        # Verify function calls
        mock_get_candidates.assert_called_once()
        mock_process_changes.assert_called_once_with(candidate_changes)

    @pytest.mark.asyncio
    @patch.object(scrap_changes, 'get_fallback_sync_candidates')
    @patch.object(scrap_changes, 'process_fallback_changes')
    @patch('asyncio.sleep')
    async def test_fallback_sync_loop_database_error_during_candidates(self, mock_sleep, mock_process_changes, mock_get_candidates):
        """Test fallback sync loop handles database errors during candidate identification"""
        # Setup mocks - get_candidates raises exception
        mock_get_candidates.side_effect = Exception("Database connection failed")
        mock_process_changes.return_value = {
            'success_count': 0,
            'error_count': 0,
            'errors': []
        }

        # Mock sleep to break the infinite loop after first iteration
        mock_sleep.side_effect = [asyncio.CancelledError()]

        # Run the function and expect it to be cancelled after first iteration
        with pytest.raises(asyncio.CancelledError):
            await scrap_changes.fallback_sync_loop()

        # Verify function calls
        mock_get_candidates.assert_called_once()
        mock_process_changes.assert_not_called()  # Should not be called due to exception

        # Verify sleep was still called (graceful error handling)
        mock_sleep.assert_called_with(60 * 60 * 12)

    @pytest.mark.asyncio
    @patch.object(scrap_changes, 'get_fallback_sync_candidates')
    @patch.object(scrap_changes, 'process_fallback_changes')
    @patch('asyncio.sleep')
    async def test_fallback_sync_loop_database_error_during_processing(self, mock_sleep, mock_process_changes, mock_get_candidates):
        """Test fallback sync loop handles database errors during processing"""
        # Setup test data
        candidate_changes = [
            {'change_id': 12345, 'repo': 'test/repo1', 'change_status': 'NEW'}
        ]

        # Setup mocks - process_changes raises exception
        mock_get_candidates.return_value = candidate_changes
        mock_process_changes.side_effect = Exception("Database connection lost during processing")

        # Mock sleep to break the infinite loop after first iteration
        mock_sleep.side_effect = [asyncio.CancelledError()]

        # Run the function and expect it to be cancelled after first iteration
        with pytest.raises(asyncio.CancelledError):
            await scrap_changes.fallback_sync_loop()

        # Verify function calls
        mock_get_candidates.assert_called_once()
        mock_process_changes.assert_called_once_with(candidate_changes)

        # Verify sleep was still called (graceful error handling)
        mock_sleep.assert_called_with(60 * 60 * 12)

    @pytest.mark.asyncio
    @patch.object(scrap_changes, 'get_fallback_sync_candidates')
    @patch.object(scrap_changes, 'process_fallback_changes')
    @patch('asyncio.sleep')
    async def test_fallback_sync_loop_none_candidates(self, mock_sleep, mock_process_changes, mock_get_candidates):
        """Test fallback sync loop when get_fallback_sync_candidates returns None"""
        # Setup mocks
        mock_get_candidates.return_value = None  # Database query returns None
        mock_process_changes.return_value = {
            'success_count': 0,
            'error_count': 0,
            'errors': []
        }

        # Mock sleep to break the infinite loop after first iteration
        mock_sleep.side_effect = [asyncio.CancelledError()]

        # Run the function and expect it to be cancelled after first iteration
        with pytest.raises(asyncio.CancelledError):
            await scrap_changes.fallback_sync_loop()

        # Verify function calls
        mock_get_candidates.assert_called_once()
        mock_process_changes.assert_not_called()  # Should not process when candidates is None

    @pytest.mark.asyncio
    @patch.object(scrap_changes, 'get_fallback_sync_candidates')
    @patch.object(scrap_changes, 'process_fallback_changes')
    @patch('asyncio.sleep')
    async def test_fallback_sync_loop_large_candidate_set(self, mock_sleep, mock_process_changes, mock_get_candidates):
        """Test fallback sync loop with large number of candidates (logging behavior)"""
        # Setup test data with more than 10 candidates
        candidate_changes = []
        for i in range(15):
            candidate_changes.append({
                'change_id': 10000 + i,
                'repo': f'test/repo{i}',
                'change_status': 'NEW'
            })

        # Setup mocks
        mock_get_candidates.return_value = candidate_changes
        mock_process_changes.return_value = {
            'success_count': 15,
            'error_count': 0,
            'errors': []
        }

        # Mock sleep to break the infinite loop after first iteration
        mock_sleep.side_effect = [asyncio.CancelledError()]

        # Run the function and expect it to be cancelled after first iteration
        with pytest.raises(asyncio.CancelledError):
            await scrap_changes.fallback_sync_loop()

        # Verify function calls
        mock_get_candidates.assert_called_once()
        mock_process_changes.assert_called_once_with(candidate_changes)

    @pytest.mark.asyncio
    @patch.object(scrap_changes, 'get_fallback_sync_candidates')
    @patch.object(scrap_changes, 'process_fallback_changes')
    @patch('asyncio.sleep')
    async def test_fallback_sync_loop_multiple_iterations(self, mock_sleep, mock_process_changes, mock_get_candidates):
        """Test fallback sync loop runs multiple iterations"""
        # Setup test data
        candidate_changes = [
            {'change_id': 12345, 'repo': 'test/repo1', 'change_status': 'NEW'}
        ]

        # Setup mocks
        mock_get_candidates.return_value = candidate_changes
        mock_process_changes.return_value = {
            'success_count': 1,
            'error_count': 0,
            'errors': []
        }

        # Mock sleep to allow 2 iterations then cancel
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        # Run the function and expect it to be cancelled after second iteration
        with pytest.raises(asyncio.CancelledError):
            await scrap_changes.fallback_sync_loop()

        # Verify function calls happened twice
        assert mock_get_candidates.call_count == 2
        assert mock_process_changes.call_count == 2
        assert mock_sleep.call_count == 2  # One successful sleep, second raises exception

    @pytest.mark.asyncio
    @patch.object(scrap_changes, 'get_fallback_sync_candidates')
    @patch.object(scrap_changes, 'process_fallback_changes')
    @patch('asyncio.sleep')
    async def test_fallback_sync_loop_unexpected_error_handling(self, mock_sleep, mock_process_changes, mock_get_candidates):
        """Test fallback sync loop handles unexpected errors in main loop"""
        # Setup mocks - unexpected error in the main try block
        mock_get_candidates.side_effect = [
            RuntimeError("Unexpected system error"),  # First iteration fails
            []  # Second iteration succeeds
        ]
        mock_process_changes.return_value = {
            'success_count': 0,
            'error_count': 0,
            'errors': []
        }

        # Mock sleep to allow 2 iterations then cancel
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        # Run the function and expect it to be cancelled after second iteration
        with pytest.raises(asyncio.CancelledError):
            await scrap_changes.fallback_sync_loop()

        # Verify function calls - should continue after error
        assert mock_get_candidates.call_count == 2
        mock_process_changes.assert_not_called()  # Not called due to first error, second has no candidates

        # Verify sleep was called twice (continues after error)
        assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    @patch.object(scrap_changes, 'get_fallback_sync_candidates')
    @patch.object(scrap_changes, 'process_fallback_changes')
    @patch('asyncio.sleep')
    @patch.object(scrap_changes.logging, 'info')
    @patch.object(scrap_changes.logging, 'error')
    @patch.object(scrap_changes.logging, 'warning')
    async def test_fallback_sync_loop_logging_behavior(self, mock_log_warning, mock_log_error, mock_log_info, mock_sleep, mock_process_changes, mock_get_candidates):
        """Test comprehensive logging behavior of fallback sync loop"""
        # Setup test data
        candidate_changes = [
            {'change_id': 12345, 'repo': 'test/repo1', 'change_status': 'NEW'},
            {'change_id': 12346, 'repo': 'test/repo2', 'change_status': 'NEW'}
        ]

        # Setup mocks with mixed results
        mock_get_candidates.return_value = candidate_changes
        mock_process_changes.return_value = {
            'success_count': 1,
            'error_count': 1,
            'errors': [
                {
                    'change_id': 12346,
                    'repo': 'test/repo2',
                    'error': 'Processing failed',
                    'stage': 'processing'
                }
            ]
        }

        # Mock sleep to break the infinite loop after first iteration
        mock_sleep.side_effect = [asyncio.CancelledError()]

        # Run the function and expect it to be cancelled after first iteration
        with pytest.raises(asyncio.CancelledError):
            await scrap_changes.fallback_sync_loop()

        # Verify logging calls
        # Check that startup logging occurred
        startup_calls = [call for call in mock_log_info.call_args_list if 'Fallback sync loop started' in str(call)]
        assert len(startup_calls) == 1

        # Check that task start logging occurred
        task_start_calls = [call for call in mock_log_info.call_args_list if 'Starting fallback sync task' in str(call)]
        assert len(task_start_calls) == 1

        # Check that candidate identification logging occurred
        identified_calls = [call for call in mock_log_info.call_args_list if 'identified 2 candidate changes' in str(call)]
        assert len(identified_calls) == 1

        # This check is now redundant since we moved it above
        # candidate_calls = [call for call in mock_log_info.call_args_list if 'identified 2 candidate changes' in str(call)]
        # assert len(candidate_calls) == 1

        # Check that completion logging occurred
        completion_calls = [call for call in mock_log_info.call_args_list if 'Fallback sync completed' in str(call)]
        assert len(completion_calls) == 1

        # Check that summary logging occurred
        summary_calls = [call for call in mock_log_info.call_args_list if 'Processing summary: 1 successful, 1 errors' in str(call)]
        assert len(summary_calls) == 1

        # Check that error warning occurred
        error_warning_calls = [call for call in mock_log_warning.call_args_list if 'encountered 1 errors' in str(call)]
        assert len(error_warning_calls) == 1

        # Check that individual error logging occurred
        individual_error_calls = [call for call in mock_log_error.call_args_list if 'Change 12346 in repo test/repo2 failed' in str(call)]
        assert len(individual_error_calls) == 1

    @pytest.mark.asyncio
    @patch.object(scrap_changes, 'get_fallback_sync_candidates')
    @patch.object(scrap_changes, 'process_fallback_changes')
    @patch('asyncio.sleep')
    async def test_fallback_sync_loop_sleep_duration(self, mock_sleep, mock_process_changes, mock_get_candidates):
        """Test that fallback sync loop sleeps for exactly 12 hours"""
        # Setup mocks
        mock_get_candidates.return_value = []
        mock_process_changes.return_value = {
            'success_count': 0,
            'error_count': 0,
            'errors': []
        }

        # Mock sleep to break the infinite loop after first iteration
        mock_sleep.side_effect = [asyncio.CancelledError()]

        # Run the function and expect it to be cancelled after first iteration
        with pytest.raises(asyncio.CancelledError):
            await scrap_changes.fallback_sync_loop()

        # Verify sleep was called with exactly 12 hours in seconds
        expected_sleep_duration = 60 * 60 * 12  # 43200 seconds
        mock_sleep.assert_called_with(expected_sleep_duration)

        # Verify the calculation is correct
        assert expected_sleep_duration == 43200

    @pytest.mark.asyncio
    @patch.object(scrap_changes, 'get_fallback_sync_candidates')
    @patch.object(scrap_changes, 'process_fallback_changes')
    @patch('asyncio.sleep')
    async def test_fallback_sync_loop_continues_after_all_error_types(self, mock_sleep, mock_process_changes, mock_get_candidates):
        """Test that fallback sync loop continues after various types of errors"""
        # Setup mocks with different error scenarios
        mock_get_candidates.side_effect = [
            Exception("Database error"),  # First iteration: database error
            [],  # Second iteration: no candidates
            [{'change_id': 12345, 'repo': 'test/repo1', 'change_status': 'NEW'}],  # Third iteration: has candidates
        ]

        mock_process_changes.side_effect = [
            Exception("Processing error"),  # Third iteration: processing error
        ]

        # Mock sleep to allow 3 iterations then cancel
        mock_sleep.side_effect = [None, None, asyncio.CancelledError()]

        # Run the function and expect it to be cancelled after third iteration
        with pytest.raises(asyncio.CancelledError):
            await scrap_changes.fallback_sync_loop()

        # Verify function calls - should continue after all errors
        assert mock_get_candidates.call_count == 3
        assert mock_process_changes.call_count == 1  # Only called on third iteration

        # Verify sleep was called 3 times (2 successful, 3rd raises exception)
        assert mock_sleep.call_count == 3

    @pytest.mark.asyncio
    @patch('asyncio.sleep')
    @patch.object(scrap_changes, 'update_fallback_processed_timestamp')
    @patch.object(scrap_changes, 'refresh_item')
    async def test_process_fallback_changes_call_order(self, mock_refresh_item, mock_update_timestamp, mock_sleep):
        """Test that timestamp update is called before refresh_item for each change"""
        mock_update_timestamp.return_value = True
        mock_refresh_item.return_value = None
        mock_sleep.return_value = None  # Mock sleep to avoid delays

        # Track call order
        call_order = []

        def timestamp_tracker(change_id, repo):
            call_order.append(f'timestamp_{change_id}')
            return True

        def refresh_tracker(change):
            call_order.append(f'refresh_{change["change_id"]}')
            return None

        def sleep_tracker(duration):
            call_order.append(f'sleep_{duration}')
            return None

        mock_update_timestamp.side_effect = timestamp_tracker
        mock_refresh_item.side_effect = refresh_tracker
        mock_sleep.side_effect = sleep_tracker

        # Test data
        candidate_changes = [
            {'change_id': 12345, 'repo': 'test/repo1', 'change_status': 'NEW'},
            {'change_id': 12346, 'repo': 'test/repo2', 'change_status': 'NEW'}
        ]

        await scrap_changes.process_fallback_changes(candidate_changes)

        # Verify call order: timestamp before refresh, then sleep, for each change
        expected_order = [
            'timestamp_12345',
            'refresh_12345',
            'sleep_2',
            'timestamp_12346',
            'refresh_12346',
            'sleep_2'
        ]
        assert call_order == expected_order

    @pytest.mark.asyncio
    @patch('asyncio.sleep')
    @patch.object(scrap_changes, 'update_fallback_processed_timestamp')
    @patch.object(scrap_changes, 'refresh_item')
    async def test_process_fallback_changes_large_batch(self, mock_refresh_item, mock_update_timestamp, mock_sleep):
        """Test processing a large batch of changes"""
        mock_update_timestamp.return_value = True
        mock_refresh_item.return_value = None
        mock_sleep.return_value = None  # Mock sleep to avoid delays

        # Create a large batch (100 changes)
        candidate_changes = []
        for i in range(100):
            candidate_changes.append({
                'change_id': 10000 + i,
                'repo': f'test/repo{i}',
                'change_status': 'NEW'
            })

        result = await scrap_changes.process_fallback_changes(candidate_changes)

        # Verify all changes were processed
        assert mock_update_timestamp.call_count == 100
        assert mock_refresh_item.call_count == 100

        # Verify sleep was called 100 times (once after each successful processing)
        assert mock_sleep.call_count == 100
        mock_sleep.assert_called_with(2)  # 2-second delay for fallback processing

        # Verify result
        expected = {
            'success_count': 100,
            'error_count': 0,
            'errors': []
        }
        assert result == expected

    @pytest.mark.asyncio
    @patch('asyncio.sleep')
    @patch.object(scrap_changes, 'update_fallback_processed_timestamp')
    @patch.object(scrap_changes, 'refresh_item')
    @patch.object(scrap_changes.logging, 'info')
    @patch.object(scrap_changes.logging, 'error')
    async def test_process_fallback_changes_logging(self, mock_log_error, mock_log_info, mock_refresh_item, mock_update_timestamp, mock_sleep):
        """Test that appropriate logging occurs during processing"""
        mock_update_timestamp.return_value = True
        mock_refresh_item.return_value = None
        mock_sleep.return_value = None  # Mock sleep to avoid delays

        candidate_changes = [
            {'change_id': 12345, 'repo': 'test/repo1', 'change_status': 'NEW'}
        ]

        await scrap_changes.process_fallback_changes(candidate_changes)

        # Verify logging calls
        mock_log_info.assert_any_call('Processing 1 fallback sync candidates')
        mock_log_info.assert_any_call('Fallback processing change 12345 in repo test/repo1')
        mock_log_info.assert_any_call('Successfully processed fallback change 12345 in repo test/repo1')
        mock_log_info.assert_any_call('Fallback processing completed: 1 successful, 0 errors')

    @pytest.mark.asyncio
    @patch('asyncio.sleep')
    @patch.object(scrap_changes, 'update_fallback_processed_timestamp')
    @patch.object(scrap_changes, 'refresh_item')
    async def test_process_fallback_changes_return_type_consistency(self, mock_refresh_item, mock_update_timestamp, mock_sleep):
        """Test that return type is consistent across different scenarios"""
        mock_update_timestamp.return_value = True
        mock_refresh_item.return_value = None
        mock_sleep.return_value = None  # Mock sleep to avoid delays

        # Test empty list
        result1 = await scrap_changes.process_fallback_changes([])
        assert isinstance(result1, dict)
        assert set(result1.keys()) == {'success_count', 'error_count', 'errors'}
        assert isinstance(result1['success_count'], int)
        assert isinstance(result1['error_count'], int)
        assert isinstance(result1['errors'], list)

        # Test with data
        candidate_changes = [{'change_id': 12345, 'repo': 'test/repo1', 'change_status': 'NEW'}]
        result2 = await scrap_changes.process_fallback_changes(candidate_changes)
        assert isinstance(result2, dict)
        assert set(result2.keys()) == {'success_count', 'error_count', 'errors'}
        assert isinstance(result2['success_count'], int)
        assert isinstance(result2['error_count'], int)
        assert isinstance(result2['errors'], list)
