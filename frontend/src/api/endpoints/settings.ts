import { apiClient } from "../client";

export interface ActorInfo {
  current_actor: string;
  is_admin: boolean;
  auth_enabled: boolean;
  tenancy_enabled: boolean;
  available_actors: string[];
  admin_actors: string[];
  api_key_configured: boolean;
  key_prefix: string | null;
}

export interface PublicSettings {
  app_name: string;
  env: string;
  auth_enabled: boolean;
  tenancy_enabled: boolean;
  admin_actors: string[];
  available_actors: string[];
}

export const settingsApi = {
  getActor: () =>
    apiClient.get<ActorInfo>("/settings/actor").then((r) => r.data),

  getPublic: () =>
    apiClient.get<PublicSettings>("/settings").then((r) => r.data),
};
