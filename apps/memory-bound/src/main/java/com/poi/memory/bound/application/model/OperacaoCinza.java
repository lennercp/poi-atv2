package com.poi.memory.bound.application.model;

import java.util.stream.IntStream;

public class OperacaoCinza implements Operacao{
    @Override
    public void executar(int[] pixels) {
        IntStream.range(0, pixels.length).parallel().forEach(i -> {
            int rgb = pixels[i];
            int r = (rgb >> 16) & 0xFF;
            int g = (rgb >> 8) & 0xFF;
            int b = rgb & 0xFF;

            int gray = (int) (0.299 * r + 0.587 * g + 0.114 * b);

            pixels[i] = (gray << 16) | (gray << 8) | gray;
        });
    }
}
