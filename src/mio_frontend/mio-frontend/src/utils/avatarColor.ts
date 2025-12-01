/**
 * Generates a consistent random color for a given name.
 * The color is generated in HSL space to ensure it is not black, white, or too light/dark.
 * 
 * @param name The name to generate the color for
 * @returns A CSS color string (hsl)
 */
export function getAvatarColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }

  // Generate HSL
  // Hue: 0-360
  const h = Math.abs(hash % 360);
  
  // Saturation: 65-85% (Vibrant but not neon)
  const s = 65 + (Math.abs(hash) % 20);
  
  // Lightness: 35-55% (Dark enough for white text, not black)
  const l = 35 + (Math.abs(hash) % 20);

  return `hsl(${h}, ${s}%, ${l}%)`;
}
