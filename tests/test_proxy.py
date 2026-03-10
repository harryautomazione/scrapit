from scraper.proxy import ProxyPool, from_directive

class TestRoundRobin:
    def test_cycles_through_proxies(self):
        pool = ProxyPool(["p1", "p2", "p3"])
        first = pool.next()
        second = pool.next()
        third = pool.next()
        assert first == "p1"
        assert second == "p2"
        assert third == "p3"

class TestRandom:
    def test_returns_from_available(self):
        pool = ProxyPool(["p1", "p2"], strategy="random")
        result = pool.next()
        assert result in ["p1", "p2"]  
        

class TestMarkFailed:
    def test_skips_failed_proxy(self):
        pool = ProxyPool(["p1", "p2"])
        pool.mark_failed("p1")
        result = pool.next()
        assert result != "p1"
        

    def test_empty_pool_returns_none(self):
        pool = ProxyPool([])
        assert pool.next() is None

    def test_failed_proxies_reset_when_all_failed(self):
        pool = ProxyPool(["p1", "p2"])
        pool.mark_failed("p1")
        pool.mark_failed("p2")
        result = pool.next()
        assert result in ["p1", "p2"]  # resets and returns one

    def test_from_directive_returns_none_when_no_proxies(self):
        result = from_directive({})
        assert result is None
            