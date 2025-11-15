// NextAuth v5 configuration
import NextAuth from 'next-auth';
import Google from 'next-auth/providers/google';

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
      authorization: {
        params: {
          scope: 'openid email profile https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/drive.readonly',
          access_type: 'offline',
          prompt: 'consent',
        },
      },
    }),
  ],
  callbacks: {
    async jwt({ token, account, user }) {
      console.log('JWT Callback - Account:', account ? 'present' : 'null');
      if (account) {
        console.log('Storing access token:', account.access_token?.substring(0, 20) + '...');
        token.accessToken = account.access_token;
        token.refreshToken = account.refresh_token;
      }
      return token;
    },
    async session({ session, token }) {
      console.log('Session Callback - Token has accessToken:', !!token.accessToken);
      session.accessToken = token.accessToken as string;
      return session;
    },
  },
  trustHost: true, // Required for NextAuth v5
});
