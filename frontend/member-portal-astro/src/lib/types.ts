import type { BilingualText } from './i18n';

export interface ChurchConfig {
  name: BilingualText;
  tagline: BilingualText;
  swish_number: string;
  bankgiro_number: string;
  org_number: string;
  membership_fee_individual: number;
  membership_fee_family: number;
  autogiro_form_url: string;
  address: string;
  youtube_channel_id: string;
}

export interface EventItem {
  title: BilingualText;
  date: string;
  time: string;
  description: BilingualText;
}

export interface Announcement {
  title: BilingualText;
  body: BilingualText;
  date: string;
}

export interface LinkItem {
  sv: string;
  am: string;
  url: string;
}

export interface SiteContent {
  church: ChurchConfig;
  upcoming: EventItem[];
  announcements: Announcement[];
  links: Record<string, LinkItem>;
  footer: { privacy: BilingualText; privacy_url: string };
}
