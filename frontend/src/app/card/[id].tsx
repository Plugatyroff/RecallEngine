import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useCallback, useState } from 'react';
import { View } from 'react-native';

import { CardHtml } from '@/components/card-html';
import { Button, ErrorMessage, Loading, Screen } from '@/components/ui';
import { Spacing } from '@/constants/theme';
import { useApi } from '@/hooks/use-api';
import { api } from '@/services/api';

/**
 * Practice a card opened from a topic: front, then answer, then the topic's next card.
 * Nothing is recorded, so practising here never changes a card's schedule; reviews that count
 * happen in review sessions.
 */
export default function CardScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const cardId = Number(id);
  const load = useCallback(async () => {
    const card = await api.card(cardId);
    const siblings = await api.cardsInTopic(card.topic_id);
    return { card, siblings };
  }, [cardId]);
  const { data, error, loading, reload } = useApi(load);
  // Which card's answer is shown; compared with the current id so a new card starts on its front
  const [revealedId, setRevealedId] = useState<number | null>(null);

  if (loading) return <Loading />;
  if (error || !data) return <ErrorMessage message={error ?? 'Card not found'} onRetry={reload} />;

  const { card, siblings } = data;
  const revealed = revealedId === card.id;
  const position = siblings.findIndex((c) => c.id === card.id);
  const next = position >= 0 ? siblings[position + 1] : undefined;

  return (
    <Screen>
      <Stack.Screen options={{ title: card.topic_name }} />
      <View style={{ flex: 1 }}>
        <CardHtml html={revealed ? card.back_html : card.front_html} />
      </View>
      <View style={{ flexDirection: 'row', gap: Spacing.two }}>
        {!revealed ? (
          <Button primary title="Show answer" onPress={() => setRevealedId(card.id)} />
        ) : next ? (
          // replace: the back arrow returns to the topic, not through every card seen
          <Button primary title="Next card" onPress={() => router.replace({ pathname: '/card/[id]', params: { id: String(next.id) } })} />
        ) : (
          <Button primary title="Back to topic" onPress={() => router.back()} />
        )}
      </View>
    </Screen>
  );
}
