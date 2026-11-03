import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useCallback, useState } from 'react';
import { View } from 'react-native';

import { CardHtml } from '@/components/card-html';
import { ReviewCard } from '@/components/review-card';
import { Button, ErrorMessage, Label, Loading, Screen } from '@/components/ui';
import { Spacing } from '@/constants/theme';
import { useApi } from '@/hooks/use-api';
import { formatInterval } from '@/lib/format';
import { api, type ReviewResult } from '@/services/api';

/** Review a single card opened from a topic, whether or not it is due. */
export default function CardScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const cardId = Number(id);
  const load = useCallback(() => api.card(cardId), [cardId]);
  const { data: card, error, loading, reload } = useApi(load);
  const [result, setResult] = useState<ReviewResult | null>(null);

  if (loading) return <Loading />;
  if (error || !card) return <ErrorMessage message={error ?? 'Card not found'} onRetry={reload} />;

  return (
    <Screen>
      <Stack.Screen options={{ title: card.topic_name }} />
      {result ? (
        <>
          <Label muted>Next review in {formatInterval(new Date(), result.due_at)}</Label>
          <View style={{ flex: 1 }}>
            <CardHtml html={card.back_html} />
          </View>
          <View style={{ flexDirection: 'row', gap: Spacing.two }}>
            <Button primary title="Back" onPress={() => router.back()} />
          </View>
        </>
      ) : (
        <ReviewCard key={card.id} card={card} onGraded={setResult} />
      )}
    </Screen>
  );
}
