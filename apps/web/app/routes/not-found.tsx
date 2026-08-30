export function loader() {
  throw new Response('Not found', {
    status: 404,
    statusText: 'Page not found',
  });
}

export default function NotFound() {
  return null;
}
