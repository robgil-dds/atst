import FormMixin from '../../mixins/form'
import textinput from '../text_input'

const createEnvironment = (name) => ({ name })

export default {
  name: 'new-project',

  mixins: [FormMixin],

  components: {
    textinput
  },

  props: {
    initialData: {
      type: Object,
      default: () => ({})
    }
  },

  data: function () {
    const {
      environment_names,
      name,
    } = this.initialData

    const environments = (
      environment_names.length > 0
      ? environment_names
      : [""]
    ).map(createEnvironment)

    return {
      environments,
      name,
    }
  },

  mounted: function () {
    this.$root.$on('onEnvironmentAdded', this.addEnvironment)
  },

  methods: {
    addEnvironment: function (event) {
      this.environments.push(createEnvironment(""))
    },

    removeEnvironment: function (index) {
      if (this.environments.length > 1) {
        this.environments.splice(index, 1)
      }
    }
  }
}
