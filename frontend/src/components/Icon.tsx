import {
  Ambulance, Bus, Car, CloudSun, Construction, Database, Gavel, GraduationCap, HardHat, HeartPulse,
  House, Landmark, MessageSquare, Network, ServerCog, Shield, Siren, Stethoscope, TreePine, TriangleAlert,
  User, Users, type LucideIcon, type LucideProps,
} from "lucide-react";

// Explicit map rather than a dynamic lookup: keeps the bundle tree-shaken and
// makes an unknown name fall back visibly instead of crashing.
const ICONS: Record<string, LucideIcon> = {
  ambulance: Ambulance, bus: Bus, car: Car, "cloud-sun": CloudSun, construction: Construction,
  gavel: Gavel, "graduation-cap": GraduationCap, "hard-hat": HardHat, "heart-pulse": HeartPulse,
  home: House, landmark: Landmark, "message-square": MessageSquare, network: Network,
  "server-cog": ServerCog, shield: Shield, siren: Siren, stethoscope: Stethoscope, trees: TreePine,
  "triangle-alert": TriangleAlert, user: User, users: Users,
};

export function Icon({ name, ...props }: { name: string } & LucideProps) {
  const C = ICONS[name] ?? Database;
  return <C {...props} />;
}
