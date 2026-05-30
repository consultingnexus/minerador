// Utilitários para formatar o telefone num link do WhatsApp Web (wa.me).

export function onlyDigits(s) {
  return (s || "").replace(/\D/g, "");
}

/**
 * Converte um telefone brasileiro num link wa.me.
 * Regras (melhor esforço):
 *  - tira tudo que não é dígito
 *  - se já vem com código do país (55 + DDD + número => 12/13 dígitos), usa direto
 *  - se vem só com DDD + número (10 ou 11 dígitos), prefixa "55" (Brasil)
 *  - caso contrário, usa os dígitos como estão
 * Retorna null quando não há número aproveitável.
 */
export function toWhatsappLink(phone) {
  const digits = onlyDigits(phone);
  if (!digits) return null;

  let full = digits;
  if (digits.startsWith("55") && digits.length >= 12) {
    full = digits;
  } else if (digits.length === 10 || digits.length === 11) {
    full = "55" + digits;
  }
  return `https://wa.me/${full}`;
}
