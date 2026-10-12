package poi.cpubound;

import java.util.Map;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

@RestController
public class PrimeController {

    public record PrimeResult(int limit, int primeCount, double computeTimeMs) {
    }

    private final PrimeService primeService;
    private final int minLimit;
    private final int maxLimit;

    public PrimeController(PrimeService primeService,
                           @Value("${primes.min-limit}") int minLimit,
                           @Value("${primes.max-limit}") int maxLimit) {
        this.primeService = primeService;
        this.minLimit = minLimit;
        this.maxLimit = maxLimit;
    }

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("status", "UP");
    }

    @GetMapping("/api/primes")
    public PrimeResult primes(@RequestParam int limit) {
        if (limit < minLimit || limit > maxLimit) {
            throw new IllegalArgumentException(
                    "limit must be between %d and %d".formatted(minLimit, maxLimit));
        }
        long start = System.nanoTime();
        int count = primeService.countPrimes(limit);
        double elapsedMs = (System.nanoTime() - start) / 1_000_000.0;
        return new PrimeResult(limit, count, elapsedMs);
    }

    @ExceptionHandler(IllegalArgumentException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Map<String, String> invalidLimit(IllegalArgumentException e) {
        return Map.of("error", e.getMessage());
    }

    @ExceptionHandler({MissingServletRequestParameterException.class, MethodArgumentTypeMismatchException.class})
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Map<String, String> badParameter() {
        return Map.of("error", "parameter 'limit' is required and must be an integer");
    }
}
