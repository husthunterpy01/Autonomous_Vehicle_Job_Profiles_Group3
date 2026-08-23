from app.utils.pagination import PageResponse


def test_paginate_list_returns_first_page():
    data = list(range(1, 26))

    result = PageResponse.paginate_list(data, page=1, page_size=10)

    assert result.items == list(range(1, 11))
    assert result.total == 25
    assert result.page == 1
    assert result.page_size == 10
    assert result.total_pages == 3


def test_paginate_list_returns_second_page():
    data = list(range(1, 26))

    result = PageResponse.paginate_list(data, page=2, page_size=10)

    assert result.items == list(range(11, 21))
    assert result.total == 25
    assert result.page == 2
    assert result.total_pages == 3


def test_paginate_list_returns_partial_last_page():
    data = list(range(1, 26))

    result = PageResponse.paginate_list(data, page=3, page_size=10)

    assert result.items == [21, 22, 23, 24, 25]
    assert result.total_pages == 3


def test_paginate_list_handles_empty_data():
    result = PageResponse.paginate_list([], page=1, page_size=10)

    assert result.items == []
    assert result.total == 0
    assert result.total_pages == 0
