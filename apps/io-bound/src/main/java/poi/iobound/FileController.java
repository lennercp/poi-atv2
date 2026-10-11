package poi.iobound;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.List;
import java.util.UUID;
import java.util.regex.Pattern;
import java.util.stream.Stream;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

// Cada arquivo vira <id>.dat, com id de 8 caracteres hexadecimais. As escritas usam DSYNC
// para irem de fato ao disco antes da resposta, em vez de ficarem só no page cache.
@RestController
@RequestMapping("/files")
public class FileController {

	record CreateRequest(String content) {}
	record AppendRequest(String content) {}
	record Created(String id) {}
	record FileEntry(String id, String content) {}

	private static final Pattern ID = Pattern.compile("[0-9a-f]{8}");

	private final Path dir;

	public FileController(@Value("${app.storage-dir}") Path dir) throws IOException {
		this.dir = Files.createDirectories(dir);
	}

	@PostMapping
	@ResponseStatus(HttpStatus.CREATED)
	public Created create(@RequestBody CreateRequest req) throws IOException {
		String id = UUID.randomUUID().toString().substring(0, 8);
		write(dataPath(id), req.content(), StandardOpenOption.CREATE_NEW);
		return new Created(id);
	}

	@GetMapping(value = "/{id}", produces = MediaType.TEXT_PLAIN_VALUE)
	public String read(@PathVariable String id) throws IOException {
		return Files.readString(dataPath(id));
	}

	@PatchMapping("/{id}")
	@ResponseStatus(HttpStatus.NO_CONTENT)
	public void append(@PathVariable String id, @RequestBody AppendRequest req) throws IOException {
		write(dataPath(id), req.content(), StandardOpenOption.APPEND);
	}

	// Lê todos os arquivos, sem paginação.
	@GetMapping
	public List<FileEntry> list() throws IOException {
		try (Stream<Path> files = Files.list(dir)) {
			return files.filter(p -> p.toString().endsWith(".dat"))
					.map(p -> p.getFileName().toString().replace(".dat", ""))
					.map(this::entry)
					.toList();
		}
	}

	@ExceptionHandler({NoSuchFileException.class, IllegalArgumentException.class})
	@ResponseStatus(HttpStatus.NOT_FOUND)
	public void notFound() {}

	private FileEntry entry(String id) {
		try {
			return new FileEntry(id, Files.readString(dataPath(id)));
		} catch (IOException e) {
			throw new UncheckedIOException(e);
		}
	}

	private void write(Path path, String text, StandardOpenOption mode) throws IOException {
		Files.writeString(path, text, StandardCharsets.UTF_8, mode, StandardOpenOption.WRITE, StandardOpenOption.DSYNC);
	}

	// Ids fora do formato (inclusive "../") viram 404.
	private Path dataPath(String id) {
		if (!ID.matcher(id).matches()) {
			throw new IllegalArgumentException(id);
		}
		return dir.resolve(id + ".dat");
	}
}
