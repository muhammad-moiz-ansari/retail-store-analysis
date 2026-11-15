const DEV_SESSION_SECRET = "local-dev-pos-session-secret";
const DEV_INTERNAL_SECRET = "local-dev-pos-secret";
const unsafeSecrets = new Set([
  DEV_SESSION_SECRET,
  DEV_INTERNAL_SECRET,
  "change-me",
  "replace-with-a-long-random-local-secret",
]);

function usableSecret(value?: string): value is string {
  return Boolean(value?.trim() && !unsafeSecrets.has(value.trim()));
}

type AuthEnv = Readonly<Record<string, string | undefined>>;

function allowsDevDefaults(env: AuthEnv) {
  return env.NODE_ENV === "development" && env.RETAILPULSE_DEV_DEFAULTS === "1";
}

export function sessionSigningSecret(env: AuthEnv = process.env, allowDefaults = true) {
  const secret = env.RETAILPULSE_SESSION_SECRET || env.POS_SESSION_SECRET || env.NEXTAUTH_SECRET;
  if (usableSecret(secret)) return secret;
  if (allowDefaults && allowsDevDefaults(env)) return DEV_SESSION_SECRET;
  return null;
}

export function resolveAuthConfig(env: AuthEnv = process.env, analytics = false) {
  const sessionSecret = sessionSigningSecret(env, !analytics);
  // The dashboard API requires the canonical credential, including in development.
  const internalSecret = env.RETAILPULSE_INTERNAL_SECRET || (analytics ? undefined : env.POS_INTERNAL_SECRET);
  if (!sessionSecret) return null;
  if (usableSecret(internalSecret)) return { sessionSecret, internalSecret };
  if (!analytics && allowsDevDefaults(env)
    && (!internalSecret || internalSecret === DEV_INTERNAL_SECRET)) {
    return { sessionSecret, internalSecret: DEV_INTERNAL_SECRET };
  }
  return null;
}
