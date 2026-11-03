import { Stack, useLocalSearchParams } from 'expo-router';
import { useCallback } from 'react';
import { View } from 'react-native';

import { CardHtml } from '@/components/card-html';
import { ErrorMessage, Label, Loading, Screen } from '@/components/ui';
import { useApi } from '@/hooks/use-api';
import { formatInterval } from '@/lib/format';
import { api, type CardDetail } from '@/services/api';

function scheduleText(card: CardDetail): string {
  if (card.status === 'new' || !card.due_at) return 'New card, not studied yet';
  const now = new Date();
  const due = new Date(card.due_at) <= now ? 'due now' : `due in ${formatInterval(now, card.due_at)}`;
  const lapses = card.lapse_count ? `, forgotten ${card.lapse_count}×` : '';
  return `${card.status} · ${due} · reviewed ${card.review_count}×${lapses}`;
}

/** One card: front and back together, and where it stands in its schedule. */
export default function CardScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const cardId = Number(id);
  const load = useCallback(() => api.card(cardId), [cardId]);
  const { data: card, error, loading, reload } = useApi(load);

  if (loading) return <Loading />;
  if (error || !card) return <ErrorMessage message={error ?? 'Card not found'} onRetry={reload} />;

  return (
    <Screen>
      <Stack.Screen options={{ title: card.topic_name }} />
      <Label muted>{scheduleText(card)}</Label>
      <View style={{ flex: 1 }}>
        {/* The back template already repeats the front above a line, as in Anki */}
        <CardHtml html={card.back_html} />
      </View>
    </Screen>
  );
}
