package store.exchange;

import java.math.BigDecimal;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.Builder;

// resposta do Exchange, igual ao enunciado: {"sell": 0.82, "buy": 0.80, "date": "2021-09-01 14:23:42", "id-account": "..."}
@Builder
public record ExchangeOut(
    BigDecimal sell,
    BigDecimal buy,
    // "YYYY-MM-DD HH:MM:SS" (nao e ISO): fica como texto, o Order nao usa
    String date,
    @JsonProperty("id-account") String idAccount
) {}
