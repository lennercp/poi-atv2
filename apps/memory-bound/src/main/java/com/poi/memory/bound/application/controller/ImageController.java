package com.poi.memory.bound.application.controller;

import com.poi.memory.bound.application.model.TipoOperacao;
import com.poi.memory.bound.application.service.ImageService;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.multipart.MultipartFile;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.IOException;

@RestController
@RequestMapping("api/imagens")
public class ImageController {
    private final ImageService imageService;

    public ImageController(ImageService imageService) {
        this.imageService = imageService;
    }

    @PostMapping(value = "/processar", consumes = MediaType.MULTIPART_FORM_DATA_VALUE, produces = MediaType.IMAGE_JPEG_VALUE)
    public ResponseEntity<byte[]> processarImagem(
            @RequestParam("file") MultipartFile file,
            @RequestParam("operacao") TipoOperacao operacao) throws IOException {

        BufferedImage imagemOriginal = ImageIO.read(file.getInputStream());

        BufferedImage imagemProcessada = imageService.processar(imagemOriginal, operacao.getOperacao());

        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ImageIO.write(imagemProcessada, "jpg", baos);

        return ResponseEntity.ok()
                .contentType(MediaType.IMAGE_JPEG)
                .body(baos.toByteArray());
    }
}
