from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist

from ..models import G2PStableID


class G2PStableIDSerializer(serializers.ModelSerializer):
    """
        Serializer for the G2PStableID model.

        This serializer converts G2PStableID instances into JSON representation
        and vice versa. It handles serialization and deserialization of G2PStableID
        objects.
    """

    def create_stable_id():
        """
            Creates a new stable identifier instance for gene-to-phenotype mapping.

            This function generates a stable identifier based on the current count of G2PStableID instances
            in the database and saves the new instance.

            Returns:
                G2PStableID: The newly created stable identifier instance.

            Raises:
                ObjectDoesNotExist: If there are no existing G2PStableID instances in the database.

            Example:
                Example usage:

                new_stable_id = create_stable_id()
                print(new_stable_id.stable_id)
                > 'G2P00001'
        """

        #Generate the sequence numbers as part of the ID 
        try:
            number_obj = G2PStableID.objects.count()
            number_obj = number_obj + 1 
            sequence_id = f"G2P{number_obj:05d}" 
        except ObjectDoesNotExist: 
            sequence_number = 1 
            sequence_id = f"G2P{sequence_number:05d}"
        
        stable_id_instance = G2PStableID(stable_id=sequence_id)
        stable_id_instance.save()

        return stable_id_instance
    
    def update_g2p_id_status(self, is_live):
        """
            Update the status of the G2P stable id.

            Parameters:
                is_live (int): The new status to set for the G2P stable ID.
                    0: The entry is not published (not live).
                    1: The entry is published (live).

            Raises:
                serializers.ValidationError: If the G2P stable ID does not exist.

            Returns:
                G2PStableID: The updated G2PStableID object.
        """
        stable_id = self.context['stable_id']

        try:
            g2p_id_obj = G2PStableID.objects.get(stable_id=stable_id)
        except G2PStableID.DoesNotExist:
            raise serializers.ValidationError({"message": f"G2P ID not found '{stable_id}'"})

        g2p_id_obj.is_live = is_live
        g2p_id_obj.save()

        return g2p_id_obj

    class Meta:
        """
            Metadata options for the G2PStableIDSerializer class.

            This Meta class provides configuration options for the G2PStableIDSerializer
            serializer class. It specifies the model to be used for serialization and
            includes/excludes certain fields from the serialized output.

            Attributes:
                model (Model): The model class associated with this serializer.
                Defines the model whose instances will be serialized and deserialized.
                exclude (list or tuple): A list of fields to be excluded from the serialized output.
                These fields will not be included in the JSON representation of the serialized object.
                In this case, the 'id' field is excluded.
        """
        model = G2PStableID
        fields = ['stable_id']
