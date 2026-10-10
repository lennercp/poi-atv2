package com.poi.memory.bound.application.model;

import java.util.stream.IntStream;

public class OperacaoInverter implements Operacao{
    @Override
    public void executar(int[] pixels) {
        IntStream.range(0, pixels.length).parallel().forEach(i -> {
            int rgb = pixels[i];
            int r = 255 - ((rgb >> 16) & 0xFF);
            int g = 255 - ((rgb >> 8) & 0xFF);
            int b = 255 - (rgb & 0xFF);

            pixels[i] = (r << 16) | (g << 8) | b;
        });
    }
}
