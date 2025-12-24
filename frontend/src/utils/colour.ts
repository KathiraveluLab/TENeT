export function getColor(score: number) {
  if (score >= 0.8) return "#7f0000";   
  if (score >= 0.6) return "#b30000";  
  if (score >= 0.4) return "#e34a33";  
  if (score >= 0.2) return "#fdbb84";  
  return "#299c06ff";                    
}
