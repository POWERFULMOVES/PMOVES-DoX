import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * Utility to merge Tailwind classes conditionally.
 * Combines clsx for conditional classes and tailwind-merge to handle conflicts.
 * 
 * @param inputs - Class names or conditional class objects.
 * @returns Merged class string.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
