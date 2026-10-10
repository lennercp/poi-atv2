package poi.cpubound;

import org.springframework.stereotype.Service;

/**
 * Counts primes by trial division. Intentionally single-threaded and without a sieve:
 * each request does real, CPU-only work that grows with the limit.
 */
@Service
public class PrimeService {

    public int countPrimes(int limit) {
        int count = 0;
        for (int n = 2; n <= limit; n++) {
            if (isPrime(n)) {
                count++;
            }
        }
        return count;
    }

    static boolean isPrime(int n) {
        if (n < 2) {
            return false;
        }
        if (n % 2 == 0) {
            return n == 2;
        }
        for (int d = 3; (long) d * d <= n; d += 2) {
            if (n % d == 0) {
                return false;
            }
        }
        return true;
    }
}
