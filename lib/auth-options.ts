import type { NextAuthOptions } from "next-auth";
import CognitoProvider from "next-auth/providers/cognito";
import CredentialsProvider from "next-auth/providers/credentials";

const cognitoConfig = process.env.COGNITO_CLIENT_ID
  && process.env.COGNITO_CLIENT_SECRET
  && process.env.COGNITO_ISSUER
  ? {
    clientId: process.env.COGNITO_CLIENT_ID,
    clientSecret: process.env.COGNITO_CLIENT_SECRET,
    issuer: process.env.COGNITO_ISSUER,
  }
  : null;

const isDevAuthAllowed = process.env.NODE_ENV !== "production"
  && process.env.DEV_AUTH_ENABLED === "true";

export const authOptions: NextAuthOptions = {
  secret: process.env.NEXTAUTH_SECRET,
  session: {
    strategy: "jwt",
    maxAge: 60 * 60,
  },
  providers: cognitoConfig
    ? [
      CognitoProvider({
        clientId: cognitoConfig.clientId,
        clientSecret: cognitoConfig.clientSecret,
        issuer: cognitoConfig.issuer,
        authorization: { params: { scope: "openid email profile" } },
      }),
    ]
    : isDevAuthAllowed
      ? [
        CredentialsProvider({
          id: "development",
          name: "Development Account",
          credentials: {
            email: { label: "Email", type: "email", placeholder: "developer@forteux.local" },
            name: { label: "Name", type: "text", placeholder: "Developer" },
          },
          async authorize(credentials) {
            const backendBase = process.env.BACKEND_API_URL;
            if (!backendBase) {
              return null;
            }
            const email = credentials?.email?.trim() || "developer@forteux.local";
            const name = credentials?.name?.trim() || "Developer";

            try {
              const res = await fetch(`${backendBase.replace(/\/+$/, "")}/auth/dev-token`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, name }),
                signal: AbortSignal.timeout(5000),
              });
              if (!res.ok) return null;
              const data = await res.json();
              return {
                id: data.user_id,
                email: data.email,
                name: data.name,
                accessToken: data.access_token,
                expiresAt: Math.floor(Date.now() / 1000) + data.expires_in,
              };
            } catch {
              return null;
            }
          },
        }),
      ]
      : [],
  callbacks: {
    async jwt({ token, account, user }) {
      if (account?.access_token) {
        token.apiAccessToken = account.access_token;
      }
      if (account?.expires_at) {
        token.apiAccessTokenExpiresAt = account.expires_at;
      }
      if (user?.accessToken) {
        token.apiAccessToken = user.accessToken;
      }
      if (user?.expiresAt) {
        token.apiAccessTokenExpiresAt = user.expiresAt;
      }
      return token;
    },
  },
};

export const isOidcConfigured = Boolean(cognitoConfig);
export const isDevAuthConfigured = isDevAuthAllowed;
