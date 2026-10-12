package poi.cpubound;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest(properties = {"primes.min-limit=2", "primes.max-limit=1000"})
@AutoConfigureMockMvc
class PrimeControllerTest {

    @Autowired
    private MockMvc mvc;

    @Test
    void healthIsUp() throws Exception {
        mvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }

    @Test
    void returnsPrimeCountAndComputeTime() throws Exception {
        mvc.perform(get("/api/primes").param("limit", "100"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.limit").value(100))
                .andExpect(jsonPath("$.primeCount").value(25))
                .andExpect(jsonPath("$.computeTimeMs").isNumber());
    }

    @Test
    void acceptsLimitsAtBothBounds() throws Exception {
        mvc.perform(get("/api/primes").param("limit", "2"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.primeCount").value(1));
        mvc.perform(get("/api/primes").param("limit", "1000"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.primeCount").value(168));
    }

    @Test
    void rejectsLimitBelowMinimum() throws Exception {
        mvc.perform(get("/api/primes").param("limit", "1"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error").value("limit must be between 2 and 1000"));
    }

    @Test
    void rejectsLimitAboveMaximum() throws Exception {
        mvc.perform(get("/api/primes").param("limit", "1001"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void rejectsMissingOrNonIntegerLimit() throws Exception {
        mvc.perform(get("/api/primes"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error").exists());
        mvc.perform(get("/api/primes").param("limit", "abc"))
                .andExpect(status().isBadRequest());
        mvc.perform(get("/api/primes").param("limit", "99999999999"))
                .andExpect(status().isBadRequest());
    }
}
