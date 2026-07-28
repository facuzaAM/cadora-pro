const PASSWORD_RULES = {
  minLength: 8,
  requireUppercase: true,
  requireNumber: true,
  requireSpecial: true,
} as const;

export function validatePassword(password: string): string | null {
  if (password.length < PASSWORD_RULES.minLength) {
    return `La contraseña debe tener al menos ${PASSWORD_RULES.minLength} caracteres`;
  }
  if (PASSWORD_RULES.requireUppercase && !/[A-Z]/.test(password)) {
    return "La contraseña debe contener al menos una mayúscula";
  }
  if (PASSWORD_RULES.requireNumber && !/[0-9]/.test(password)) {
    return "La contraseña debe contener al menos un número";
  }
  if (PASSWORD_RULES.requireSpecial && !/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
    return "La contraseña debe contener al menos un carácter especial";
  }
  return null;
}
