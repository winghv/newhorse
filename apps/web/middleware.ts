import createMiddleware from "next-intl/middleware";
import { routing } from "./i18n/routing";

export default createMiddleware(routing);

export const config = {
  // Match all paths EXCEPT:
  // - /api/* (proxied to backend via next.config.js rewrites)
  // - /_next/* (Next.js internals)
  // - /_vercel/* (Vercel internals)
  // - Static files with extensions (favicon.ico, images, etc.)
  matcher: ["/((?!api|_next|_vercel|.*\\..*).*)"],
};
