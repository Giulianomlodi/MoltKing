
def behavior(state, actions, strategy, processed):
    """
    Cleanup old directives. This is a placeholder behavior that signals
    the need for directive cleanup at the API level.
    The actual cleanup happens via the issue_directives with high priority.
    """
    # This behavior monitors but doesn't take direct action
    # It relies on directive_cleanup task in the API to prune old directives
    pass
