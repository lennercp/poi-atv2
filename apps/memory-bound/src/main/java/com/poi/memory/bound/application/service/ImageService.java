package com.poi.memory.bound.application.service;
import com.poi.memory.bound.application.model.Operacao;
import org.springframework.stereotype.Service;

import java.awt.image.BufferedImage;
import java.awt.image.DataBufferInt;

@Service
public class ImageService {
    public BufferedImage processar(BufferedImage original, Operacao operacao) {
        BufferedImage imagemSaida = new BufferedImage(
                original.getWidth(), original.getHeight(), BufferedImage.TYPE_INT_RGB);

        imagemSaida.getGraphics().drawImage(original, 0, 0, null);

        int[] pixels = ((DataBufferInt) imagemSaida.getRaster().getDataBuffer()).getData();

        operacao.executar(pixels);

        return imagemSaida;
    }
}
