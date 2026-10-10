package com.poi.memory.bound.application.model;

public enum TipoOperacao {
    CINZA(new OperacaoCinza()),
    INVERTER(new OperacaoInverter());

    private final Operacao operacao;

    TipoOperacao(Operacao operacao) {
        this.operacao = operacao;
    }

    public Operacao getOperacao() {
        return operacao;
    }
}
