// Safe to commit. These are PUBLIC client settings, not secrets.
// The Supabase anon/publishable key is designed for browser use; RLS is mandatory.
export const SUPABASE_URL = 'https://YOUR_PROJECT_REF.supabase.co';
export const SUPABASE_ANON_KEY = 'YOUR_SUPABASE_PUBLISHABLE_OR_ANON_KEY';
export const LMC_DEFAULT_CENTER = [18.4088, 76.5604]; // approximate Latur city center; replace with approved extent
export const LMC_DEFAULT_ZOOM = 12;
