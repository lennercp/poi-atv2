package poi.cpubound;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class PrimeServiceTest {

    private final PrimeService service = new PrimeService();

    @Test
    void identifiesPrimes() {
        assertTrue(PrimeService.isPrime(2));
        assertTrue(PrimeService.isPrime(3));
        assertTrue(PrimeService.isPrime(7919));
        assertFalse(PrimeService.isPrime(1));
        assertFalse(PrimeService.isPrime(9));
        assertFalse(PrimeService.isPrime(7917));
    }

    @Test
    void countsKnownValuesOfPrimeCountingFunction() {
        assertEquals(1, service.countPrimes(2));
        assertEquals(4, service.countPrimes(10));
        assertEquals(25, service.countPrimes(100));
        assertEquals(168, service.countPrimes(1_000));
        assertEquals(78_498, service.countPrimes(1_000_000));
    }
}
