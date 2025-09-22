import { redirect } from 'next/navigation'

export default function HomePage() {
  // Redirect to login since we need tenant selection
  redirect('/login')
}