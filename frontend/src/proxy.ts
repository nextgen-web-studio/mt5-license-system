import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function proxy(request: NextRequest) {
  // If user is trying to access /admin or its subdirectories
  if (request.nextUrl.pathname.startsWith('/admin')) {
    // Check if they have the auth token cookie
    const token = request.cookies.get('admin_token')?.value;

    if (!token) {
      // No token, redirect to login page
      return NextResponse.redirect(new URL('/login', request.url));
    }
  }

  // If trying to access login page while already authenticated
  if (request.nextUrl.pathname === '/login') {
    const token = request.cookies.get('admin_token')?.value;
    if (token) {
      return NextResponse.redirect(new URL('/admin/orders', request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/admin/:path*', '/login'],
};

