def _chunk_and_dispatch_tasks(
    items: list,
    task_to_run: callable,
    chunk_size: int,
    *task_args,
    **task_kwargs,
) -> list:
    """
    Dispatches tasks in chunks to avoid broker overload.

    Args:
        items (list): A list of items to process (e.g., file paths).
        task_to_run (callable): The Celery task function to call.
        chunk_size (int): The number of items to process in each chunk.
        *task_args: Positional arguments to pass to the task function.
        **task_kwargs: Keyword arguments to pass to the task function.

    Returns:
        list: A list of task IDs for the dispatched tasks.
    """
    all_task_ids = []
    for i in range(0, len(items), chunk_size):
        chunk = items[i : i + chunk_size]  # noqa 203
        for item in chunk:
            # The task_to_run is expected to take the item as its first arg
            tid = task_to_run(item, *task_args, **task_kwargs)
            all_task_ids.append(tid)
    return all_task_ids
