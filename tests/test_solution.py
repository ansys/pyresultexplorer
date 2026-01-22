def test_solution_crud(rx, rst_multiple_connections):
    # create a new solution
    sol = rx.create_solution(
        name="Test Solution",
        result_provider_name="Local",
        file_path=rst_multiple_connections,
    )

    assert sol.name == "Test Solution"
    assert sol.id is not None

    assert sol.n_elements == 246
    assert sol.n_nodes == 844
    assert sol.n_sets == 1

    assert (
        len(sol.bodies) == 4
    )  # temporarily because splitMeshBy is defaulted to false in the web api
    assert sol.unsupported_element_types[0] == "SURF154"

    # list solutions
    solutions = rx.list_solutions()
    assert any(s.id == sol.id for s in solutions)

    # get solution
    fetched_sol = rx.get_solution(solution_id=sol.id)
    assert fetched_sol.id == sol.id
    assert fetched_sol.name == sol.name
    assert fetched_sol.n_elements == sol.n_elements

    # delete solution
    rx.delete_solution(solution_id=sol.id)

    # verify deletion
    solutions = rx.list_solutions()
    assert all(s.id != sol.id for s in solutions)
